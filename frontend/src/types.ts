// Types for the Final Display format per PRD
export interface CustomerRef {
  salutation: string;
  first_name: string;
  last_name: string;
  full_name: string;
}

export interface QBAddress {
  line1: string;
  city: string;
  state: string;
  zip: string;
}

export interface DisplayPayerInfo {
  customer_ref: CustomerRef;
  qb_organization_name: string;
  qb_address: QBAddress;
  qb_email: string;
  qb_phone: string;
}

export interface DisplayPaymentInfo {
  payment_ref: string;
  amount: string;
  payment_date: string;
  deposit_date: string;
  deposit_method: string;
  memo: string;
}

export interface DonationStatus {
  matched: boolean;
  new_customer: boolean;
  sent_to_qb: boolean;
  address_updated: boolean;
  edited: boolean;
}

export interface FinalDisplayDonation {
  payer_info: DisplayPayerInfo;
  payment_info: DisplayPaymentInfo;
  status: DonationStatus;
  _id?: string;
  _match_data?: any;
}

// Legacy types for backward compatibility
export interface PaymentInfo {
  Payment_Ref: string;
  Amount: number;
  Payment_Method?: string;
  Payment_Date?: string;
  Check_Date?: string;
  Postmark_Date?: string;
  Deposit_Date?: string;
  Deposit_Method?: string;
  Memo?: string;
}

export interface PayerInfo {
  Aliases?: string[];
  Salutation?: string;
  Organization_Name?: string;
}

export interface ContactInfo {
  Address_Line_1?: string;
  City?: string;
  State?: string;
  ZIP?: string;
  Email?: string;
  Phone?: string;
}

export interface Donation {
  PaymentInfo: PaymentInfo;
  PayerInfo?: PayerInfo;
  ContactInfo?: ContactInfo;
  status?: DonationStatus;
  match_data?: any;
}

export interface ProcessingMetadata {
  files_processed: number;
  raw_count: number;
  valid_count: number;
  duplicate_count: number;
  matched_count?: number;
}

export interface UploadResponse {
  success: boolean;
  data: {
    upload_id: string;
    files: {
      original_name: string;
      stored_name: string;
      size: number;
    }[];
  };
}

export interface ProcessResponse {
  success: boolean;
  data: {
    donations: FinalDisplayDonation[];
    raw_donations?: Donation[];
    metadata: ProcessingMetadata;
  };
}

// QuickBooks related types
export interface QuickBooksAuthStatus {
  authenticated: boolean;
  realm_id?: string;
  access_token_valid?: boolean;
  access_token_expires_at?: string;
  refresh_token_valid?: boolean;
  refresh_token_expires_at?: string;
}

export interface QuickBooksAuthResponse {
  success: boolean;
  data?: {
    auth_url?: string;
    state?: string;
    session_id?: string;
    realm_id?: string;
    expires_at?: string;
  };
  error?: string;
}
