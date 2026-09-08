// Shared API model types

export interface Patient {
  id: number;
  patient_number: string;
  first_name: string;
  last_name: string;
  full_name: string;
  date_of_birth: string;
  gender: 'M' | 'F' | 'O';
  created_at: string;
}

export interface LabRequest {
  request_id: string;
  patient_number: string;
  patient_name: string;
  test_code: string;
  test_name: string;
  status: 'PENDING' | 'SENT' | 'REJECTED' | 'ERROR' | 'COMPLETED';
  lis_order_number: string;
  rejection_reason: string;
  requested_at: string;
  updated_at: string;
}

export interface LabResult {
  result_id: string;
  result_value: string;
  unit: string;
  reference_range: string;
  is_abnormal: boolean;
  notes: string;
  performed_by: string;
  verified_by: string;
  completed_at: string;
}

export interface LabOrder {
  order_number: string;
  hms_request_id: string;
  patient_number: string;
  patient_name: string;
  patient_date_of_birth: string;
  test_code: string;
  test_name: string;
  status: 'ACCEPTED' | 'REJECTED' | 'IN_PROGRESS' | 'COMPLETED';
  result: LabResult | null;
  received_at: string;
  updated_at: string;
}

export interface CatalogEntry {
  code: string;
  name: string;
  description: string;
  is_active: boolean;
}

export interface IntegrationLogEntry {
  transaction_id: string;
  request_id: string | null;
  endpoint: string;
  method: string;
  status_code: number;
  status: string;
  error_message: string;
  created_at: string;
}

export interface SubmitRequestResponse {
  detail: string;
  request_id: string;
  status: string;
  lis_order_number: string;
  rejection_reason?: string;
  upstream_status_code?: number;
}

export interface ResultResponse {
  request_id: string;
  patient_number: string;
  test_code: string;
  lis_order_number: string;
  order_number: string;
  order_status: string;
  result: LabResult;
}
