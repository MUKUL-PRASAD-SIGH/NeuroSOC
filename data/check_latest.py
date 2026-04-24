import json
from kafka import KafkaConsumer

c = KafkaConsumer(
    'extracted-features',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    consumer_timeout_ms=5000
)

for msg in c:
    data = json.loads(msg.value.decode('utf-8'))
    if data.get('n_packets') == 7:
        print("FOUND REALISTIC FLOW:")
        print(json.dumps(data, indent=2))
        break
c.close()
