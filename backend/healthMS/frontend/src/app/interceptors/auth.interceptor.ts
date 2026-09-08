import {
  HttpErrorResponse,
  HttpInterceptorFn,
  HttpRequest,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService, Side } from '../services/auth.service';

let refreshing = false;

/**
 * Attaches the JWT of the active side (HMS or Lab) to every /api request.
 * - LIS endpoints always use the Lab session.
 * - Other requests use the side sent in the X-Auth-Side header, falling
 *   back to the currently active side.
 * - On 401 the token is refreshed once and the request retried.
 */
export const apiInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  if (!req.url.startsWith('/api')) {
    return next(req);
  }

  const side: Side = req.url.includes('/api/lis/')
    ? 'lab'
    : ((req.headers.get('X-Auth-Side') as Side | null) ?? auth.active());
  const headers = req.headers.delete('X-Auth-Side');

  const token = auth.token(side);
  const authed = token
    ? req.clone({ headers: headers.set('Authorization', `Bearer ${token}`) })
    : req.clone({ headers });

  return next(authed).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401 || !auth.isLoggedIn(side) || refreshing) {
        return throwError(() => error);
      }
      // One transparent refresh attempt, then retry the original request.
      refreshing = true;
      return auth.refresh(side).pipe(
        switchMap((access) => {
          refreshing = false;
          const retry: HttpRequest<unknown> = req.clone({
            headers: req.headers.set('Authorization', `Bearer ${access}`),
          });
          return next(retry);
        }),
        catchError((err) => {
          refreshing = false;
          auth.logout(side);
          return throwError(() => err);
        })
      );
    })
  );
};
