import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, ApiError } from '../../services/api.service';
import { AuthService, Side } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  imports: [FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  api = inject(ApiService);
  auth = inject(AuthService);
  router = inject(Router);

  side: Side = 'hms';
  username = 'hms_demo';
  password = 'HmsDemo#2024';
  busy = signal(false);
  error = signal<string | null>(null);

  switchSide(side: Side) {
    this.side = side;
    this.username = side === 'hms' ? 'hms_demo' : 'lab_admin';
    this.password = side === 'hms' ? 'HmsDemo#2024' : 'LabAdmin#2024';
    this.error.set(null);
  }

  async submit() {
    if (!this.username || !this.password) {
      this.error.set('Username and password are required.');
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.api.login(this.side, this.username, this.password);
      this.router.navigateByUrl('/dashboard');
    } catch (e) {
      this.error.set((e as ApiError).message);
    } finally {
      this.busy.set(false);
    }
  }
}
