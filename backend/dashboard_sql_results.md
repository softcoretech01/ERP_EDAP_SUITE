# Dashboard LLM Generation Results

### Q: What is the total procurement spend this month?
**Triggered Hints:**
```
'date' maps to -> Columns: prdate, createddt
'purchase' maps to -> Tables: tbl_purchaseorder_header, tbl_purchaserequisition_header
```
**Generated SQL:**
```sql
SELECT SUM(nettotal) AS total_spend
FROM tbl_purchaseorder_header
WHERE podate >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND podate < DATE_FORMAT(CURDATE() + INTERVAL 1 MONTH, '%Y-%m-01');
```
---
### Q: How much spend is under approval?
**Triggered Hints:**
```
Map 'under approval' -> check `po_gm_isapproved = 0` or `pr_gm_isapproved = 0`
```
**Generated SQL:**
```sql
SELECT SUM(nettotal) AS total_spend_under_approval
FROM tbl_purchaseorder_header
WHERE po_gm_isapproved = 0;
```
---
### Q: What is the total committed spend?
**Triggered Hints:**
```
Map 'committed spend' -> sum `tbl_purchaseorder_header.nettotal`
```
**Generated SQL:**
```sql
SELECT SUM(`tbl_purchaseorder_header`.`nettotal`) AS TotalCommittedSpend
FROM `tbl_purchaseorder_header`;
```
---
### Q: What is the total unpaid invoice value?
**Triggered Hints:**
```
Map 'unpaid invoice' -> SUM(`tbl_irnreceipt_header`.`balance`)
'irn receipt' maps to -> Columns: irndate, irnno | Tables: tbl_invoicereceipt_attachment, tbl_irnreceipt_header, tbl_irnreceipt_detail
```
**Generated SQL:**
```sql
SELECT SUM(t1.balance) AS TotalUnpaidInvoiceValue
FROM tbl_irnreceipt_header t1
JOIN tbl_irnreceipt_attachment t2 ON t1.receiptnote_hdr_id = t2.receiptnote_hdr_id
WHERE t1.status = 'Active' AND t1.balance > 0;
```
---
### Q: Track procurement cycle from PR to Payment.
**Triggered Hints:**
```
'purchase requisition' maps to -> Columns: prdate, prno, pr_gm_isapproved, po_gm_isapproved, prid | Tables: tbl_purchaserequisition_header
'purchase' maps to -> Tables: tbl_purchaseorder_header, tbl_purchaserequisition_header
```
**Generated SQL:**
```sql
SELECT 
    ppr.prid AS pr_id,
    ppr.prno AS pr_number,
    ppr.prdate AS pr_date,
    ppoh.poid AS po_id,
    ppoh.pono AS po_number,
    ppoh.podate AS po_date,
    ppoh.supplierid AS supplier_id,
    ppoh.createddt AS po_created_date,
    ppoh.subtotal AS base_amount,
    ppoh.taxvalue AS tax,
    ppoh.vatvalue AS vat,
    ppoh.nettotal AS total_value,
    CASE 
        WHEN ppr.ispoutil = 0 THEN 'Pending'
        ELSE 'Approved'
    END AS pr_status,
    CASE 
        WHEN ppoh.IsGrnRaised = 0 THEN 'Pending'
        ELSE 'Received'
    END AS po_status
FROM 
    tbl_PurchaseRequisition_Header ppr
LEFT JOIN 
    tbl_purchaseorder_header ppoh ON ppr.prid = ppoh.po_ref_id
WHERE 
    ppr.status IN ('Pending', 'Approved')
ORDER BY 
    pr_date, po_created_date;
```
---
### Q: Which PRs have not yet become Purchase Orders?
**Triggered Hints:**
```
'purchase' maps to -> Tables: tbl_purchaseorder_header, tbl_purchaserequisition_header
Map 'PRs not POs' -> filter `tbl_PurchaseRequisition_Header.IsPOUtil = 0`
```
**Generated SQL:**
```sql
SELECT prid, prno, prdate, ispoutil, pr_gm_isapproved, status
FROM tbl_PurchaseRequisition_Header
WHERE IsPOUtil = 0;
```
---
