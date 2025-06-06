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

export interface DonationStatus {
  matched?: boolean;
  newCustomer?: boolean;
  sentToQB?: boolean;
  addressUpdated?: boolean;
  edited?: boolean;
}

export interface Donation {
  PaymentInfo: PaymentInfo;
  PayerInfo?: PayerInfo;
  ContactInfo?: ContactInfo;
  status?: DonationStatus;
}

export interface ProcessingMetadata {
  files_processed: number;
  raw_count: number;
  valid_count: number;
  duplicate_count: number;
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
    donations: Donation[];
    metadata: ProcessingMetadata;
  };
}
