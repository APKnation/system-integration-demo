import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, throwError } from 'rxjs';

export type Side = 'hms' | 'lab';

interface Session {
  side: Side;
  username: string;
  access: string;
  refresh: string;
}

const STORAGE_KEY = 'hmslis.sessions';

/**
 * Holds one JWT session per "system": the HMS service account and the
 * Lab staff account, mirroring the service-to-service split of the backend.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly sessions = signal<Record<Side, Session | null>>({
    hms: null,
    lab: null,
  });

  private http = inject(HttpClient);

  constructor() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        this.sessions.set(JSON.parse(raw));
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }

  /** Which side is "active" for pages that need a single token. */
  readonly active = signal<Side>('hms');

  set(session: Session) {
    this.sessions.update((s) => ({ ...s, [session.side]: session }));
    this.active.set(session.side);
    this.persist();
  }

  logout(side: Side) {
    this.sessions.update((s) => ({ ...s, [side]: null }));
    if (this.active() === side) {
      this.active.set(this.sessions()['hms'] ? 'hms' : 'lab');
    }
    this.persist();
  }

  logoutAll() {
    this.sessions.set({ hms: null, lab: null });
    localStorage.removeItem(STORAGE_KEY);
  }

  get(side: Side): Session | null {
    return this.sessions()[side];
  }

  token(side: Side): string | null {
    return this.sessions()[side]?.access ?? null;
  }

  username(side: Side): string | null {
    return this.sessions()[side]?.username ?? null;
  }

  isLoggedIn(side: Side): boolean {
    return !!this.sessions()[side];
  }

  isActiveLoggedIn(): boolean {
    return this.isLoggedIn(this.active());
  }

  /** Refresh the JWT for a side; resolves with the new access token. */
  refresh(side: Side): Observable<string> {
    const session = this.sessions()[side];
    if (!session) {
      return throwError(() => new Error('Not logged in'));
    }
    return this.http
      .post<{ access: string }>('/api/auth/token/refresh/', {
        refresh: session.refresh,
      })
      .pipe(
        map((res) => {
          this.set({ ...session, access: res.access });
          return res.access;
        })
      );
  }

  private persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.sessions()));
  }
}
