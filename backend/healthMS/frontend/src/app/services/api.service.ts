import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, firstValueFrom, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService, Side } from './auth.service';
import {
  CatalogEntry,
  IntegrationLogEntry,
  LabOrder,
  LabRequest,
  LabResult,
  Patient,
  ResultResponse,
  SubmitRequestResponse,
} from '../models';

/** Normalized API error surfaced to components. */
export interface ApiError {
  status: number;
  message: string;
  details?: unknown;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private handle(err: HttpErrorResponse): Observable<never> {
    let message = err.error?.detail ?? err.message ?? 'Request failed';
    if (err.status === 0) {
      message = 'Cannot reach the API — is the backend running?';
    }
    const apiError: ApiError = {
      status: err.status,
      message,
      details: err.error,
    };
    return throwError(() => apiError);
  }

  private get<T>(url: string, side: Side): Observable<T> {
    return this.http
      .get<T>(url, { headers: { 'X-Auth-Side': side } })
      .pipe(catchError((e) => this.handle(e)));
  }

  private post<T>(url: string, body: unknown, side: Side): Observable<T> {
    return this.http
      .post<T>(url, body, { headers: { 'X-Auth-Side': side } })
      .pipe(catchError((e) => this.handle(e)));
  }

  // ------------------------------ auth ------------------------------

  async login(side: Side, username: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http
        .post<{ access: string; refresh: string }>('/api/auth/token/', {
          username,
          password,
        })
        .pipe(catchError((e) => this.handle(e)))
    );
    this.auth.set({ side, username, access: res.access, refresh: res.refresh });
  }

  // ------------------------------ HMS ------------------------------

  listPatients(): Observable<Patient[]> {
    return this.get<Patient[]>('/api/hms/patients/', 'hms');
  }

  createPatient(payload: {
    patient_number: string;
    first_name: string;
    last_name: string;
    date_of_birth: string;
    gender: string;
  }): Observable<Patient> {
    return this.post<Patient>('/api/hms/patients/', payload, 'hms');
  }

  listLabRequests(): Observable<LabRequest[]> {
    return this.get<LabRequest[]>('/api/hms/lab-requests/', 'hms');
  }

  submitLabRequest(payload: {
    patient_number: string;
    test_code: string;
    test_name: string;
    request_id?: string;
  }): Observable<SubmitRequestResponse> {
    return this.post<SubmitRequestResponse>(
      '/api/hms/lab-requests/',
      payload,
      'hms'
    );
  }

  getResult(requestId: string): Observable<ResultResponse> {
    return this.get<ResultResponse>(
      `/api/hms/lab-requests/${requestId}/result/`,
      'hms'
    );
  }

  // ------------------------------ LIS ------------------------------

  listOrders(): Observable<LabOrder[]> {
    return this.get<LabOrder[]>('/api/lis/orders/', 'lab');
  }

  getOrder(requestId: string): Observable<LabOrder> {
    return this.get<LabOrder>(`/api/lis/orders/${requestId}/`, 'lab');
  }

  processOrder(
    requestId: string,
    result: Partial<LabResult>
  ): Observable<{ detail: string; order_number: string; order_status: string }> {
    return this.post(
      `/api/lis/orders/${requestId}/process/`,
      result,
      'lab'
    );
  }

  getCatalog(): Observable<CatalogEntry[]> {
    return this.get<CatalogEntry[]>('/api/lis/catalog/', 'lab');
  }

  /** Deliberately unauthenticated call used by the demo (expect 401). */
  anonCatalogCheck(): Observable<unknown> {
    return this.http.get('/api/lis/catalog/').pipe(catchError((e) => this.handle(e)));
  }

  // --------------------------- integration ---------------------------

  getLogs(limit = 60): Observable<IntegrationLogEntry[]> {
    return this.get<IntegrationLogEntry[]>(
      `/api/logs/?limit=${limit}`,
      'lab'
    );
  }
}
