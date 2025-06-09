import React, { useState, useEffect } from 'react';
import './AddCustomerModal.css';

interface CustomerFormData {
  displayName: string;
  firstName?: string;
  lastName?: string;
  organizationName?: string;
  email?: string;
  phone?: string;
  addressLine1?: string;
  city?: string;
  state?: string;
  zip?: string;
}

interface AddCustomerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CustomerFormData) => void;
  initialData?: Partial<CustomerFormData>;
}

const initialFormState: CustomerFormData = {
  displayName: '',
  firstName: '',
  lastName: '',
  organizationName: '',
  email: '',
  phone: '',
  addressLine1: '',
  city: '',
  state: '',
  zip: '',
};

const AddCustomerModal: React.FC<AddCustomerModalProps> = ({ isOpen, onClose, onSubmit, initialData }) => {
  const [formData, setFormData] = useState<CustomerFormData>(initialFormState);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setFormData(prev => ({ ...initialFormState, ...initialData }));
      } else {
        setFormData(initialFormState);
      }
      setError(''); // Clear any previous errors when modal opens
    }
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.displayName.trim()) {
      setError('Customer Reference (Display Name) is required.');
      return;
    }
    setError('');
    onSubmit(formData);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2>{initialData ? 'Edit Customer' : 'Add New Customer'}</h2>
        {error && <p className="error-message">{error}</p>}
        <form onSubmit={handleSubmit}>
          <div>
            <label htmlFor="displayName">Customer Reference (Display Name):*</label>
            <input type="text" id="displayName" name="displayName" value={formData.displayName} onChange={handleChange} required />
          </div>
          <div>
            <label htmlFor="firstName">First Name:</label>
            <input type="text" id="firstName" name="firstName" value={formData.firstName} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="lastName">Last Name:</label>
            <input type="text" id="lastName" name="lastName" value={formData.lastName} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="organizationName">Organization Name:</label>
            <input type="text" id="organizationName" name="organizationName" value={formData.organizationName} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="email">Email:</label>
            <input type="email" id="email" name="email" value={formData.email} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="phone">Phone:</label>
            <input type="tel" id="phone" name="phone" value={formData.phone} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="addressLine1">Address Line 1:</label>
            <input type="text" id="addressLine1" name="addressLine1" value={formData.addressLine1} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="city">City:</label>
            <input type="text" id="city" name="city" value={formData.city} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="state">State / Province:</label>
            <input type="text" id="state" name="state" value={formData.state} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="zip">Zip / Postal Code:</label>
            <input type="text" id="zip" name="zip" value={formData.zip} onChange={handleChange} />
          </div>
          <div className="modal-actions">
            <button type="submit" className="button-primary">Save Customer</button>
            <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddCustomerModal;
