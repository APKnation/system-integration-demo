import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService, ApiError } from '../../services/api.service';
import { IntegrationLogEntry } from '../../models';

@Component({
  selector: 'app-logs',
  imports: [FormsModule],
  templateUrl: './logs.html',
  styleUrl: './logs.css',
})
export class Logs implements OnInit {
  api = inject(ApiService);
  logs = signal<IntegrationLogEntry[]>([]);
  busy = signal(false);
  error = signal<string | null>(null);
  limit = 100;

  /** Labels the side of the integration a log entry belongs to. */
  sideOf(l: IntegrationLogEntry): 'int' | 'lis' | 'hms' {
    const INT = new Set([
      'ORDER_SUBMITTED',
      'RESULT_RETRIEVED',
      'CONNECTION_ERROR',
      'AUTH_ERROR',
      'SERVER_ERROR',
      'REJECTED_BY_LIS',
    ]);
    if (INT.has(l.status)) return 'int';
    return l.endpoint.startsWith('/api/lis') ? 'lis' : 'hms';
  }

  ngOnInit(): void {
    void this.load();
  }

  async load(): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    try {
      this.logs.set(await firstValueFrom(this.api.getLogs(this.limit)));
    } catch (e) {
      this.error.set((e as ApiError).message);
    } finally {
      this.busy.set(false);
    }
  }
}
