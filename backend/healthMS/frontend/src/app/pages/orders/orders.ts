import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService, ApiError } from '../../services/api.service';
import { LabOrder } from '../../models';

@Component({
  selector: 'app-orders',
  imports: [FormsModule],
  templateUrl: './orders.html',
  styleUrl: './orders.css',
})
export class Orders implements OnInit {
  api = inject(ApiService);
  orders = signal<LabOrder[]>([]);
  busy = signal(false);
  message = signal<{ type: string; text: string } | null>(null);
  processing = signal<LabOrder | null>(null);

  resultForm = {
    result_value: '',
    unit: '',
    reference_range: '',
    is_abnormal: false,
    notes: '',
    performed_by: 'Tech. Neema Kileo',
    verified_by: 'Dr. Aisha Mwaky',
  };

  ngOnInit(): void {
    void this.load();
  }

  async load(): Promise<void> {
    this.busy.set(true);
    try {
      this.orders.set(await firstValueFrom(this.api.listOrders()));
    } catch (e) {
      this.message.set({ type: 'err', text: (e as ApiError).message });
    } finally {
      this.busy.set(false);
    }
  }

  openProcess(order: LabOrder): void {
    this.processing.set(order);
    const abnormalDefaults = order.test_code === 'LIP';
    this.resultForm = {
      result_value: abnormalDefaults ? '9.6' : '4.8',
      unit: abnormalDefaults ? 'mmol/L' : '10^3/uL',
      reference_range: abnormalDefaults ? '3.5-5.5' : '4.0-10.0',
      is_abnormal: abnormalDefaults,
      notes: abnormalDefaults
        ? 'Cholesterol elevated; lifestyle review advised.'
        : 'Within normal limits.',
      performed_by: 'Tech. Neema Kileo',
      verified_by: 'Dr. Aisha Mwaky',
    };
  }

  async saveResult(): Promise<void> {
    const order = this.processing();
    if (!order) return;
    this.busy.set(true);
    this.message.set(null);
    try {
      const res = await firstValueFrom(
        this.api.processOrder(order.hms_request_id, { ...this.resultForm })
      );
      this.message.set({ type: 'ok', text: `${res.detail} (${res.order_number})` });
      this.processing.set(null);
      await this.load();
    } catch (e) {
      this.message.set({ type: 'err', text: (e as ApiError).message });
    } finally {
      this.busy.set(false);
    }
  }

  cancelProcess(): void {
    this.processing.set(null);
  }
}
