import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { sideGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login').then(m => m.Login),
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/dashboard/dashboard').then(m => m.Dashboard),
    canActivate: [authGuard],
  },
  {
    path: 'patients',
    loadComponent: () => import('./pages/patients/patients').then(m => m.Patients),
    canActivate: [authGuard],
  },
  {
    path: 'lab-requests',
    loadComponent: () => import('./pages/lab-requests/lab-requests').then(m => m.LabRequests),
    canActivate: [authGuard],
  },
  {
    path: 'orders',
    loadComponent: () => import('./pages/orders/orders').then(m => m.Orders),
    canActivate: [sideGuard('lab')],
  },
  {
    path: 'catalog',
    loadComponent: () => import('./pages/catalog/catalog').then(m => m.Catalog),
    canActivate: [sideGuard('lab')],
  },
  {
    path: 'logs',
    loadComponent: () => import('./pages/logs/logs').then(m => m.Logs),
    canActivate: [authGuard],
  },
  { path: '**', redirectTo: 'dashboard' },
];
