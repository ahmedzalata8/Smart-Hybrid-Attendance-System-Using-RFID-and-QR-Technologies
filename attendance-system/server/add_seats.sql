DO $$
DECLARE
  cid uuid := 'dfca288d-4fb6-40b5-acdc-c65ebd3c2546';
  labels text[] := ARRAY['A','B','C','D','E'];
  r int;
  c int;
  lbl text;
BEGIN
  FOR r IN 0..4 LOOP
    FOR c IN 0..4 LOOP
      lbl := labels[r+1] || (c+1)::text;
      IF NOT EXISTS (SELECT 1 FROM seats WHERE classroom_id = cid AND row = r AND col = c) THEN
        INSERT INTO seats (id, classroom_id, label, row, col, tag_id)
        VALUES (gen_random_uuid(), cid, lbl, r, c, 'RFID-TAG-' || lbl);
      END IF;
    END LOOP;
  END LOOP;
END $$;

SELECT label, row, col, tag_id FROM seats
WHERE classroom_id = 'dfca288d-4fb6-40b5-acdc-c65ebd3c2546'
ORDER BY row, col;
