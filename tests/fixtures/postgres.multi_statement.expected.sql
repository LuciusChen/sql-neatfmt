SELECT * FROM public.order_payoil WHERE code = 'P001';

DELETE FROM order_payoil
WHERE code = 'P002'
  AND deleted = FALSE;
