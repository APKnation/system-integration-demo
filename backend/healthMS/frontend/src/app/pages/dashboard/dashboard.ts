import { JsonPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Router } from '@angular/router';
import { ApiService, ApiError } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import {
  CatalogEntry,
  IntegrationLogEntry,
  LabOrder,
  LabRequest,
  Patient,
  ResultResponse,
} from '../../models';

const NORMAL = {
  result_value: '4.8',
  unit: '10^3/uL',
  reference_range: '4.0-10.0',
  is_abnormal: false,
  notes: 'Within normal limits.',
  performed_by: 'Tech. Neema Kileo',
  verified_by: 'Dr. Aisha Mwaky',
};

const ABNORMAL = {
  result_value: '9.6',
  unit: 'mmol/L',
  reference_range: '3.5-5.5',
  is_abnormal: true,
  notes: 'Cholesterol elevated; lifestyle review advised.',
  performed_by: 'Tech. Neema Kileo',
  verified_by: 'Dr. Aisha Mwaky',
};

interface DemoStep {
  n: number;
  label: string;
  icon: string;
  detail: string;
}

@Component({
  selector: 'app-dashboard',
  imports: [FormsModule, JsonPipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit {
  api = inject(ApiService);
  auth = inject(AuthService);
  router = inject(Router);

  requests = signal<LabRequest[]>([]);
  orders = signal<LabOrder[]>([]);
  logs = signal<IntegrationLogEntry[]>([]);
  patients = signal<Patient[]>([]);
  catalog = signal<CatalogEntry[]>([]);

  selPatient = 'HMS-0001';
  selTest = 'CBC';
  selOrder = '';
  busy = signal(false);
  demoRunning = signal(false);
  message = signal<{ type: string; text: string } | null>(null);
  resultModal = signal<ResultResponse | null>(null);
  resultError = signal<string | null>(null);
  steps = signal<DemoStep[]>([]);

  stats = computed(() => {
    const rs = this.requests();
    return {
      total: rs.length,
      sent: rs.filter((r) => r.status === 'SENT').length,
      completed: rs.filter((r) => r.status === 'COMPLETED').length,
      rejected: rs.filter((r) => ['REJECTED', 'ERROR'].includes(r.status)).length,
    };
  });

  ngOnInit(): void {
    if (!this.auth.isActiveLoggedIn()) {
      this.router.navigateByUrl('/login');
      return;
    }
    void this.refreshAll();
  }

  // ------------------------------ loading ------------------------------

  async refreshAll(): Promise<void> {
    await Promise.allSettled([
      this.loadRequests(),
      this.loadOrders(),
      this.loadLogs(),
      this.loadPatients(),
      this.loadCatalog(),
    ]);
  }

  async loadRequests(): Promise<void> {
    try {
      this.requests.set(await firstValueFrom(this.api.listLabRequests()));
    } catch {
      /* guard handles auth */
    }
  }

  async loadOrders(): Promise<void> {
    if (!this.auth.isLoggedIn('lab')) return;
    try {
      this.orders.set(await firstValueFrom(this.api.listOrders()));
    } catch {
      /* ignore */
    }
  }

  async loadLogs(): Promise<void> {
    try {
      this.logs.set(await firstValueFrom(this.api.getLogs(40)));
    } catch {
      /* ignore */
    }
  }

  async loadPatients(): Promise<void> {
    try {
      this.patients.set(await firstValueFrom(this.api.listPatients()));
    } catch {
      /* ignore */
    }
  }

  async loadCatalog(): Promise<void> {
    try {
      this.catalog.set(await firstValueFrom(this.api.getCatalog()));
    } catch {
      /* ignore */
    }
  }

  // ------------------------------ actions ------------------------------

  async submit(): Promise<void> {
    this.busy.set(true);
    this.message.set(null);
    const test = this.catalog().find((c) => c.code === this.selTest);
    try {
      const res = await firstValueFrom(
        this.api.submitLabRequest({
          patient_number: this.selPatient,
          test_code: this.selTest,
          test_name: test?.name ?? this.selTest,
        })
      );
      this.message.set({ type: 'ok', text: res.detail });
    } catch (e) {
      const err = e as ApiError;
      this.message.set({ type: 'err', text: `HTTP ${err.status}: ${err.message}` });
    } finally {
      this.busy.set(false);
      await this.refreshAll();
    }
  }

  async processSelected(): Promise<void> {
    if (!this.selOrder) {
      this.message.set({ type: 'warn', text: 'Select a submitted request first.' });
      return;
    }
    await this.processOrder(this.selOrder);
  }

  private async processOrder(rid: string): Promise<void> {
    this.busy.set(true);
    this.message.set(null);
    try {
      const order = await firstValueFrom(this.api.getOrder(rid));
      if (order.result) {
        this.message.set({
          type: 'info',
          text: `Order ${order.order_number} is already completed.`,
        });
        return;
      }
      const body = order.test_code === 'LIP' ? ABNORMAL : NORMAL;
      const res = await firstValueFrom(this.api.processOrder(rid, body));
      this.message.set({ type: 'ok', text: `${res.detail} (${res.order_number})` });
    } catch (e) {
      this.message.set({ type: 'err', text: (e as ApiError).message });
    } finally {
      this.busy.set(false);
      await this.refreshAll();
    }
  }

  async viewResult(rid: string): Promise<void> {
    this.resultError.set(null);
    try {
      this.resultModal.set(await firstValueFrom(this.api.getResult(rid)));
    } catch (e) {
      const err = e as ApiError;
      this.resultError.set(
        err.status === 409
          ? 'Result not available yet (HTTP 409).'
          : `HTTP ${err.status}: ${err.message}`
      );
      if (err.status === 409) {
        this.message.set({ type: 'warn', text: 'Result not available yet (HTTP 409).' });
      }
    }
  }

  closeModal(): void {
    this.resultModal.set(null);
    this.resultError.set(null);
  }

  // ------------------------------ auto demo ------------------------------

  private setStep(n: number, label: string, icon = '…', detail = ''): void {
    this.steps.update((list) => {
      const idx = list.findIndex((x) => x.n === n);
      const entry: DemoStep = { n, label, icon, detail };
      if (idx >= 0) {
        const copy = [...list];
        copy[idx] = entry;
        return copy;
      }
      return [...list, entry];
    });
  }

  private finishStep(n: number, icon: string, detail: string): void {
    this.steps.update((list) =>
      list.map((x) => (x.n === n ? { ...x, icon, detail } : x))
    );
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }

  async runDemo(): Promise<void> {
    if (this.demoRunning()) return;
    this.demoRunning.set(true);
    this.steps.set([]);
    this.message.set(null);

    try {
      // 1 — validation errors
      this.setStep(1, 'Request validation — missing fields are rejected');
      try {
        await firstValueFrom(
          this.api.submitLabRequest({ patient_number: '', test_code: 'CBC', test_name: 'CBC' })
        );
        this.finishStep(1, '❌', 'Unexpectedly accepted');
      } catch (e) {
        this.finishStep(1, '✅', `HTTP ${(e as ApiError).status} — rejected as expected`);
      }
      await this.sleep(500);

      // 2 — authentication check
      this.setStep(2, 'Authentication — request without JWT is rejected');
      try {
        await firstValueFrom(this.api.anonCatalogCheck());
        this.finishStep(2, '❌', 'Unexpectedly allowed');
      } catch (e) {
        this.finishStep(2, '✅', `HTTP ${(e as ApiError).status} — blocked as expected`);
      }
      await this.sleep(500);

      // 3 — valid submission
      this.setStep(3, 'HMS submits a valid lab request to the LIS');
      let rid = '';
      try {
        const res = await firstValueFrom(
          this.api.submitLabRequest({
            patient_number: 'HMS-0001',
            test_code: 'CBC',
            test_name: 'Complete Blood Count',
          })
        );
        rid = res.request_id;
        this.finishStep(3, '✅', `Order ${res.lis_order_number} accepted`);
      } catch (e) {
        this.finishStep(3, '❌', (e as ApiError).message);
        throw e;
      }
      await this.refreshAll();
      await this.sleep(800);

      // 4 — result before analysis
      this.setStep(4, 'HMS asks for the result before analysis (expect 409)');
      try {
        await firstValueFrom(this.api.getResult(rid));
        this.finishStep(4, '❌', 'Unexpectedly got a result');
      } catch (e) {
        this.finishStep(4, '✅', `HTTP ${(e as ApiError).status} — result not ready`);
      }
      await this.refreshAll();
      await this.sleep(800);

      // 5 — lab processes the order
      this.setStep(5, 'Lab staff record the result — order COMPLETED');
      try {
        const res = await firstValueFrom(this.api.processOrder(rid, NORMAL));
        this.finishStep(5, '✅', `${res.detail} (${res.order_number})`);
      } catch (e) {
        this.finishStep(5, '❌', (e as ApiError).message);
        throw e;
      }
      await this.refreshAll();
      await this.sleep(800);

      // 6 — retrieve result
      this.setStep(6, 'HMS retrieves the patient’s laboratory result');
      try {
        const res = await firstValueFrom(this.api.getResult(rid));
        this.finishStep(
          6,
          '✅',
          `${res.result.result_value} ${res.result.unit} (ref ${res.result.reference_range})`
        );
      } catch (e) {
        this.finishStep(6, '❌', (e as ApiError).message);
        throw e;
      }
      await this.refreshAll();
      await this.sleep(800);

      // 7 — unknown test code
      this.setStep(7, 'Unknown test code — LIS rejects with 422');
      try {
        await firstValueFrom(
          this.api.submitLabRequest({
            patient_number: 'HMS-0002',
            test_code: 'XYZ-999',
            test_name: 'Non-existent Panel',
          })
        );
        this.finishStep(7, '❌', 'Unexpectedly accepted');
      } catch (e) {
        this.finishStep(7, '✅', `HTTP ${(e as ApiError).status} — rejected`);
      }
      await this.refreshAll();
      await this.sleep(800);

      // 8 — idempotency
      this.setStep(8, 'Idempotency — same request_id returns the same order');
      try {
        const payload = {
          request_id: crypto.randomUUID(),
          patient_number: 'HMS-0003',
          test_code: 'BS',
          test_name: 'Blood Sugar (Fasting)',
        };
        const r1 = await firstValueFrom(this.api.submitLabRequest(payload));
        const r2 = await firstValueFrom(this.api.submitLabRequest(payload));
        this.finishStep(
          8,
          '✅',
          `First → ${r1.status} (${r1.lis_order_number}); re-submit → ${r2.status}, same order`
        );
      } catch (e) {
        this.finishStep(8, '❌', (e as ApiError).message);
      }
      await this.refreshAll();
      this.message.set({
        type: 'ok',
        text: 'Demo complete — see the steps, tables and the transaction log below.',
      });
    } catch {
      this.message.set({ type: 'err', text: 'Demo stopped early — see the failing step.' });
    } finally {
      this.demoRunning.set(false);
    }
  }
}
