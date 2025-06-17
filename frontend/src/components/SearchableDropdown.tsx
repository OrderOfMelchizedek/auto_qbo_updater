import React, { useState, useEffect, useCallback } from 'react';
import { Loader, ChevronDown } from 'lucide-react';
import './SearchableDropdown.css';
import { apiService } from '../services/api';

interface SearchableDropdownItem {
  Id: string;
  Name: string;
  FullyQualifiedName?: string;
  [key: string]: any;
}

interface SearchableDropdownProps {
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  searchEndpoint: string;
  displayField?: 'Name' | 'FullyQualifiedName';
  defaultSearchTerm?: string;
  className?: string;
  required?: boolean;
  emptyMessage?: string;
  renderItem?: (item: SearchableDropdownItem) => React.ReactNode;
  getItemsFromResponse?: (data: any) => SearchableDropdownItem[];
}

const SearchableDropdown: React.FC<SearchableDropdownProps> = ({
  placeholder,
  value,
  onChange,
  searchEndpoint,
  displayField = 'FullyQualifiedName',
  defaultSearchTerm = '',
  className = '',
  required = false,
  emptyMessage = 'No items found',
  renderItem,
  getItemsFromResponse
}) => {
  const [searchTerm, setSearchTerm] = useState(defaultSearchTerm);
  const [items, setItems] = useState<SearchableDropdownItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<SearchableDropdownItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedItem, setSelectedItem] = useState<SearchableDropdownItem | null>(null);
  const [debounceTimeout, setDebounceTimeout] = useState<NodeJS.Timeout | null>(null);

  // Fetch all items on component mount
  useEffect(() => {
    fetchItems();
  }, [searchEndpoint]);

  // Find selected item when value changes
  useEffect(() => {
    if (value && items.length > 0) {
      const item = items.find(i => i.Id === value);
      setSelectedItem(item || null);
      if (item) {
        setSearchTerm(item[displayField] || item.Name || '');
      }
    }
  }, [value, items, displayField]);

  // Filter items based on search term
  useEffect(() => {
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      const filtered = items.filter(item =>
        (item.Name || '').toLowerCase().includes(search) ||
        (item.FullyQualifiedName || '').toLowerCase().includes(search)
      );
      setFilteredItems(filtered);
    } else {
      setFilteredItems(items);
    }
  }, [searchTerm, items]);

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.get(searchEndpoint);

      if (response.data.success) {
        let fetchedItems: SearchableDropdownItem[] = [];

        if (getItemsFromResponse) {
          fetchedItems = getItemsFromResponse(response.data.data);
        } else {
          // Default extraction logic
          fetchedItems = response.data.data.accounts ||
                        response.data.data.items ||
                        response.data.data ||
                        [];
        }

        setItems(fetchedItems);
        setError(null);
      } else {
        throw new Error(response.data.error || 'Failed to fetch items');
      }
    } catch (err: any) {
      console.error('Error fetching items:', err);
      setError(err.message || 'Failed to fetch items');
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchEndpoint, getItemsFromResponse]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newSearchTerm = e.target.value;
    setSearchTerm(newSearchTerm);
    setShowDropdown(true);

    // If user clears the input, clear the selection
    if (!newSearchTerm) {
      setSelectedItem(null);
      onChange('');
    }
  };

  const handleSelectItem = (item: SearchableDropdownItem) => {
    setSelectedItem(item);
    setSearchTerm(item[displayField] || item.Name || '');
    onChange(item.Id);
    setShowDropdown(false);
  };

  const handleInputFocus = () => {
    setShowDropdown(true);
  };

  const handleInputBlur = () => {
    // Use timeout to allow click events on dropdown items
    setTimeout(() => {
      setShowDropdown(false);
      // If no item is selected and there's text, clear it
      if (!selectedItem && searchTerm) {
        setSearchTerm('');
      }
    }, 200);
  };

  const defaultRenderItem = (item: SearchableDropdownItem) => (
    <>
      <div className="item-name">{item[displayField] || item.Name}</div>
      {displayField === 'FullyQualifiedName' && item.Name !== item.FullyQualifiedName && (
        <div className="item-detail">{item.Name}</div>
      )}
    </>
  );

  return (
    <div className={`searchable-dropdown ${className}`}>
      <div className="searchable-input-wrapper">
        <input
          type="text"
          placeholder={placeholder}
          value={searchTerm}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onBlur={handleInputBlur}
          className="searchable-input"
          required={required}
        />
        <div className="input-icons">
          {isLoading && <Loader className="search-spinner" size={16} />}
          <ChevronDown className="dropdown-icon" size={16} />
        </div>
      </div>

      {error && <div className="dropdown-error">{error}</div>}

      {showDropdown && !isLoading && (
        <div className="searchable-dropdown-results">
          {filteredItems.length === 0 ? (
            <div className="no-results">{emptyMessage}</div>
          ) : (
            filteredItems.map((item) => (
              <div
                key={item.Id}
                onClick={() => handleSelectItem(item)}
                className={`dropdown-item ${selectedItem?.Id === item.Id ? 'selected' : ''}`}
              >
                {renderItem ? renderItem(item) : defaultRenderItem(item)}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default SearchableDropdown;
