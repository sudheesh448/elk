after building and up containers
for changing the password of kibana
curl -u elastic:changeme -X POST "http://localhost:9200/\_security/user/kibana_system/\_password" -H 'Content-Type: application/json' -d '{
"password" : "changeme"
}'

docker exec -it docker-elk-elasticsearch-1 /bin/bash
docker-compose up --build -d
