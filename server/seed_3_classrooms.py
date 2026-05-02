import sys
import asyncio
import uuid
import random
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.department import Department

async def main():
    async with AsyncSessionLocal() as db:
        print("Seeding 3 classrooms with digital twins...")
        
        # Get existing department
        result = await db.execute(select(Department).limit(1))
        dept = result.scalar_one_or_none()
        
        if not dept:
            dept_id = str(uuid.uuid4())
            await db.execute(text(
                "INSERT INTO departments (id, name, code) VALUES (:id, 'Computer Science', 'CS')"
            ), {"id": dept_id})
        else:
            dept_id = dept.id

        layouts = [(6, 6, "Alpha"), (4, 5, "Beta"), (5, 8, "Gamma")]
        
        for rows, cols, name_suffix in layouts:
            classroom_id = str(uuid.uuid4())
            room_name = f"Room {name_suffix}-{random.randint(100, 999)}"
            
            await db.execute(text(
                "INSERT INTO classrooms (id, name, department_id, layout_rows, layout_cols) "
                "VALUES (:id, :name, :dept_id, :rows, :cols) ON CONFLICT DO NOTHING"
            ), {"id": classroom_id, "name": room_name, "dept_id": dept_id, "rows": rows, "cols": cols})
            
            # Create seats
            for r in range(rows):
                for c in range(cols):
                    sid = str(uuid.uuid4())
                    tag = f"RFID-{name_suffix}-{r}-{c}-{random.randint(1000,9999)}"
                    label = f"{chr(65+r)}{c+1}"
                    await db.execute(text(
                        "INSERT INTO seats (id, classroom_id, label, row, col, tag_id) "
                        "VALUES (:id, :cid, :label, :row, :col, :tag) ON CONFLICT DO NOTHING"
                    ), {"id": sid, "cid": classroom_id, "label": label, "row": r, "col": c, "tag": tag})
            
            print(f"✅ Created Classroom: {room_name} ({rows}x{cols}) with {rows*cols} seats.")

        await db.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
