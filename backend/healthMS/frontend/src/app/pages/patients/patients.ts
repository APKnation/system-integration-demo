import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService, ApiError } from '../../services/api.service';
import { Patient } from '../../models';

@Component({
  selector: 'app-patients',
  imports: [FormsModule],
  templateUrl: './patients.html',
  styleUrl: './patients.css',
})
export class Patients implements OnInit {
  api = inject(ApiService);
  patients = signal<Patient[]>([]);
  busy = signal(false);
  message = signal<{ type: string; text: string } | null>(null);

  model = { patient_number: '', first_name: '', last_name: '', date_of_birth: '', gender: 'F' };

  ngOnInit(): void {
    void this.load();
  }

  async load(): Promise<void> {
    this.busy.set(true);
    try {
      this.patients.set(await firstValueFrom(this.api.listPatients()));
    } catch (e) {
      this.message.set({ type: 'err', text: (e as ApiError).message });
    } finally {
      this.busy.set(false);
    }
  }

  async create(): Promise<void> {
    this.busy.set(true);
    this.message.set(null);
    try {
      await firstValueFrom(this.api.createPatient(this.model));
      this.message.set({ type: 'ok', text: `Patient ${this.model.patient_number} created.` });
      this.model = { patient_number: '', first_name: '', last_name: '', date_of_birth: '', gender: 'F' };
      await this.load();
    } catch (e) {
      this.message.set({ type: 'err', text: (e as ApiError).message });
    } finally {
      this.busy.set(false);
    }
  }
}
