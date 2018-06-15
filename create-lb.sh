# Copyright Google Inc. 2017
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

export BACKEND_PORT=30033

echo "Creating firewall rules..."
gcloud compute firewall-rules create wsc-explorer-lb7-fw --target-tags wsc-explorer-node --allow "tcp:${BACKEND_PORT}" --source-ranges 130.211.0.0/22,35.191.0.0/16

echo "Creating health checks..."
gcloud compute health-checks create http wsc-explorer-basic-check --port $BACKEND_PORT --healthy-threshold 1 --unhealthy-threshold 10 --check-interval 60 --timeout 60

echo "Creating an instance group..."
export INSTANCE_GROUP=$(gcloud container clusters describe wsc-explorer-cluster --format="value(instanceGroupUrls)" | awk -F/ '{print $NF}')

echo "Creating named ports..."
gcloud compute instance-groups managed set-named-ports $INSTANCE_GROUP --named-ports "port${BACKEND_PORT}:${BACKEND_PORT}"

echo "Creating the backend service..."
gcloud compute backend-services create wsc-explorer-service --protocol HTTP --health-checks wsc-explorer-basic-check --port-name "port${BACKEND_PORT}" --global

echo "Connecting instance group to backend service..."
export INSTANCE_GROUP_ZONE=$(gcloud config get-value compute/zone)
gcloud compute backend-services add-backend wsc-explorer-service --instance-group $INSTANCE_GROUP --instance-group-zone $INSTANCE_GROUP_ZONE --global

echo "Creating URL map..."
gcloud compute url-maps create wsc-explorer-urlmap --default-service wsc-explorer-service

echo "Uploading SSL certificates..."
gcloud compute ssl-certificates create wsc-explorer-ssl-cert --certificate /tmp/wsc-explorer-ssl/ssl.crt --private-key /tmp/wsc-explorer-ssl/ssl.key

echo "Creating HTTPS target proxy..."
gcloud compute target-https-proxies create wsc-explorer-https-proxy --url-map wsc-explorer-urlmap --ssl-certificates wsc-explorer-ssl-cert

echo "Creating global forwarding rule..."
gcloud compute forwarding-rules create wsc-explorer-gfr --address $STATIC_IP --global --target-https-proxy wsc-explorer-https-proxy --ports 443
