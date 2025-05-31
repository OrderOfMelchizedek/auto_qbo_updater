// Enhancements for displaying enriched payment data

// Add visual indicators for enriched data
function addEnrichmentIndicators(tr, donation) {
    // Find the customer status cell
    const statusCell = tr.querySelector('td:nth-child(11)'); // Adjust based on actual column position

    if (!statusCell) {return;}

    let indicators = '';

    // Address needs update indicator
    if (donation.addressNeedsUpdate) {
        indicators += `
            <span class="badge bg-warning me-1"
                  title="Address differs from QuickBooks. Click to review.">
                <i class="fas fa-map-marker-alt"></i> Address Update
            </span>`;
    }

    // Email updated indicator
    if (donation.emailUpdated) {
        indicators += `
            <span class="badge bg-info me-1"
                  title="New email address found">
                <i class="fas fa-envelope"></i> +Email
            </span>`;
    }

    // Phone updated indicator
    if (donation.phoneUpdated) {
        indicators += `
            <span class="badge bg-info me-1"
                  title="New phone number found">
                <i class="fas fa-phone"></i> +Phone
            </span>`;
    }

    // Multiple emails/phones indicator
    if (donation.qb_email && Array.isArray(donation.qb_email) && donation.qb_email.length > 1) {
        indicators += `
            <span class="badge bg-secondary me-1"
                  title="${donation.qb_email.length} email addresses">
                ${donation.qb_email.length} <i class="fas fa-envelope"></i>
            </span>`;
    }

    if (donation.qb_phone && Array.isArray(donation.qb_phone) && donation.qb_phone.length > 1) {
        indicators += `
            <span class="badge bg-secondary me-1"
                  title="${donation.qb_phone.length} phone numbers">
                ${donation.qb_phone.length} <i class="fas fa-phone"></i>
            </span>`;
    }

    // Add indicators to status cell
    if (indicators) {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'enrichment-indicators mt-1';
        indicatorDiv.innerHTML = indicators;
        statusCell.appendChild(indicatorDiv);
    }
}

// Enhanced address display with comparison
function showAddressComparison(donation) {
    if (!donation.addressNeedsUpdate) {return;}

    const modalHtml = `
        <div class="modal fade" id="addressComparisonModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Address Comparison - ${donation['Donor Name']}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Current QuickBooks Address</h6>
                                <div class="card">
                                    <div class="card-body">
                                        <p class="mb-1">${donation.qbo_address_line_1 || ''}</p>
                                        <p class="mb-1">${donation.qbo_city || ''}, ${donation.qbo_state || ''} ${donation.qbo_zip || ''}</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h6>Extracted Address <span class="badge bg-warning">New</span></h6>
                                <div class="card border-warning">
                                    <div class="card-body">
                                        <p class="mb-1">${donation['Address - Line 1'] || ''}</p>
                                        <p class="mb-1">${donation.City || ''}, ${donation.State || ''} ${donation.ZIP || ''}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="mt-3">
                            <p class="text-muted">The extracted address differs significantly from the QuickBooks address. Would you like to update QuickBooks with the new address?</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Keep Current</button>
                        <button type="button" class="btn btn-warning" onclick="updateQBOAddress('${donation.internalId}')">
                            <i class="fas fa-sync"></i> Update QuickBooks Address
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('addressComparisonModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('addressComparisonModal'));
    modal.show();
}



// Hook into existing render function
const originalRenderDonationTable = window.renderDonationTable;
window.renderDonationTable = function() {
    // Call original render
    originalRenderDonationTable();

    // Add enrichment indicators to each row
    donations.forEach(donation => {
        const tr = document.querySelector(`tr[data-id="${donation.internalId}"]`);
        if (tr) {
            addEnrichmentIndicators(tr, donation);

            // Add click handler for address comparison
            if (donation.addressNeedsUpdate) {
                const addressCell = tr.querySelector('td[data-field="Address - Line 1"]');
                if (addressCell) {
                    addressCell.style.cursor = 'pointer';
                    addressCell.classList.add('text-warning');
                    addressCell.title = 'Click to compare addresses';
                    addressCell.addEventListener('click', (e) => {
                        e.stopPropagation();
                        showAddressComparison(donation);
                    });
                }
            }
        }
    });
};

// Add styles for enrichment indicators
const style = document.createElement('style');
style.textContent = `
    .enrichment-indicators {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }

    .enrichment-indicators .badge {
        font-size: 0.75rem;
        cursor: help;
    }

    .enrichment-indicators .badge i {
        margin-right: 0.25rem;
    }

    td[data-field="Address - Line 1"].text-warning {
        text-decoration: underline;
        text-decoration-style: dotted;
    }

    .card.border-warning {
        border-width: 2px;
    }
`;
document.head.appendChild(style);
