import json
import time
from datetime import datetime

people_data = []

for i, row in people.iterrows():
    user_ids = [x["id_value"] for x in json.loads(row[4])["user_ids"]]
    user_ids_str = ", ".join(user_ids)

    person_rec = {}
    person_rec["id"] = row[0]
    person_rec["first_name"] = row[1]
    person_rec["last_name"] = row[2]
    person_rec["text"] = f"{row[1]} {row[2]} IDs: {user_ids_str}"
    person_rec["role"] = row[3] if not isinstance(row[3], float) else ""
    person_rec["user_ids"] = json.dumps(json.loads(row[4])["user_ids"])
    person_rec["relations"] = json.dumps(json.loads(row[5])["relations"])
    person_rec["created_at"] = int(datetime.now().timestamp())

    people_data.append(person_rec)

for person in people_data:
    person_id = person.pop("id")
    index.update(id=person_id, metadata={"text": person["text"]}, namespace=namespace)
    time.sleep(1)
