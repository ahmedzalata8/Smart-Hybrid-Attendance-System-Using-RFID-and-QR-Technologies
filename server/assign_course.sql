DO $$
DECLARE
  shawky_id uuid;
  dept_id uuid;
BEGIN
  SELECT id, department_id INTO shawky_id, dept_id FROM users WHERE email = 'dr.shawky@aast.edu';
  IF shawky_id IS NOT NULL THEN
    INSERT INTO courses (id, code, name, department_id, lecturer_id) 
    VALUES (gen_random_uuid(), 'CS401', 'Artificial Intelligence', dept_id, shawky_id);
  END IF;
END $$;
