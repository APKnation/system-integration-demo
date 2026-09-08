import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService, ApiError } from '../../services/api.service';
import { CatalogEntry, LabRequest, ResultResponse } from '../../models';

@Component({
  selector: 'app-lab-requests',
  imports: [FormsModule],
  templateUrl: './lab-requests.html',
  styleUrl: './lab-requests.css',
})
export class LabRequests implements OnInit {
  api = inject(ApiService);
  requests = signal<LabRequest[]>([]);
  catalog = signal<CatalogEntry[]>([]);
  busy = signal(false);
  message = signal<{ type: string; text: string } | null>(null);
  resultModal = signal<ResultResponse | null>(null);

  model = { patient_number: '', test_code: 'CBC', request_id: '' };

  ngOnInit(): void {
    void this.load();
    void this.loadCatalog();
  }

  async load(): Promise<void> {
    this.busy.set(true);
    try {
      this.requests.set(await firstValueFrom(this.api.listLabRequests()));
    } catch (e) {
      this.message.set({ type: 'err', text: (e as ApiError).message });
    } finally {
      this.busy.set(false);
    }
  }

  async loadCatalog(): Promise<void> {
    try {
      this.catalog.set(await firstValueFrom(this.api.getCatalog()));
    } catch {
      /* catalog needs lab session; ignore on this page */
    }
  }

  async submit(): Promise<void> {
    this.busy.set(true);
    this.message.set(null);
    const test = this.catalog().find((c) => c.code === this.model.test_code);
    try {
      const payload: Record<string, string> = {
        patient_number: this.model.patient_number,
        test_code: this.model.test_code,
        test_name: test?.name ?? this.model.test_code,
      };
      if (this.model.request_id.trim()) {
        payload['request_id'] = this.model.request_id.trim();
      }
      const res = await firstValueFrom(
        this.api.submitLabRequest(payload as never)
      );
      this.message.set({ type: 'ok', text: res.detail });
      this.model.request_id = '';
      await this.load();
    } catch (e) {
      const err = e as ApiError;
      this.message.set({ type: 'err', text: `HTTP ${err.status}: ${err.message}` });
    } finally {
      this.busy.set(false);
    }
  }

  async viewResult(rid: string): Promise<void> {
    this.message.set(null);
    try {
      this.resultModal.set(await firstValueFrom(this.api.getResult(rid)));
    } catch (e) {
      const err = e as ApiError;
      this.message.set({
        type: err.status === 409 ? 'warn' : 'err',
        text:
          err.status === 409
            ? 'Result not available yet — the LIS has not completed this order (HTTP 409).'
            : `HTTP ${err.status}: ${err.message}`,
      });
    }
  }

  closeModal(): void {
    this.resultModal.set(null);
  }
}
