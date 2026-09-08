import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Requires any active session (HMS or Lab). */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isActiveLoggedIn()) {
    return true;
  }
  return router.createUrlTree(['/login']);
};

/** Requires a specific side's session (e.g. 'lab' for LIS pages). */
export const sideGuard =
  (side: 'hms' | 'lab'): CanActivateFn =>
  () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (auth.isLoggedIn(side)) {
      return true;
    }
    return router.createUrlTree(['/login']);
  };
