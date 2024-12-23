### 환경 변수 설정
```
export PROJECT_ID=$GOOGLE_CLOUD_PROJECT
export REGION=us-central1

export CLUSTER=mr-gke

export K8S_SERVICE_ACCOUNT=mr-ksa
export GCP_SERVICE_ACCOUNT=mr-gsa

export GEMINI_MODEL=gemini-1.5-flash-002
```

### 서비스 활성화
```
gcloud services enable \
 cloudbuild.googleapis.com \
 aiplatform.googleapis.com \
 run.googleapis.com \
 --project $PROJECT_ID
```

### 실습 코드 복사
```
git clone https://github.com/kiwonl/movie-recommendation
cd ~/movie-recommendation
```

# Artifact Registry 에 Docker 저장소 생성
```
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository" \
  --project=$PROJECT_ID
```

# Cloud Build 를 활용하여 컨테이너 빌드
```
gcloud builds submit --tag=${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/movie-recommendation
```

# Google Kubernetes Engine
### GKE Autopilot 클러스터 생성
```
gcloud container clusters create-auto $CLUSTER \
    --location=$REGION --async
```

### GKE 클러스터 인증
```
gcloud container clusters get-credentials $CLUSTER --region $REGION
```

### K8s Config (Deployment, Service) 에 환경변수 값 적용
```
sed -i 's/${K8S_SERVICE_ACCOUNT}/'${K8S_SERVICE_ACCOUNT}'/g' k8s.yaml
sed -i 's/${REGION}/'${REGION}'/g' k8s.yaml
sed -i 's/${PROJECT_ID}/'${PROJECT_ID}'/g' k8s.yaml
sed -i 's/${GEMINI_MODEL}/'${GEMINI_MODEL}'/g' k8s.yaml
```

### Workload Identity Federation for GKE
```
# Vertex AI 호출을 위한 SA 생성
gcloud iam service-accounts create ${GCP_SERVICE_ACCOUNT} \
 --project ${PROJECT_ID}

# Vertex AI 호출을 위한 Rule 부여
gcloud projects add-iam-policy-binding ${PROJECT_ID}  \
 --member "serviceAccount:${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"  \
 --role "roles/aiplatform.user"

# GSA 와 KSA 바인딩
gcloud iam service-accounts add-iam-policy-binding ${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com \
 --role roles/iam.workloadIdentityUser \
 --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/${K8S_SERVICE_ACCOUNT}]"

# GSA 와 KSA 바인딩 (KSA 에 annotation 추가)
kubectl annotate serviceaccount ${K8S_SERVICE_ACCOUNT} \
iam.gke.io/gcp-service-account=${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com
```

### K8s Config (Deployment, Service) 배포
```
kubectl apply -f k8s.yaml
```

### 테스트
```
export ENDPOINT=[External-ip of Service]

curl -X POST -H "Content-Type: application/json" -d '{
  "movies": ["Despicable Me 4", "Inside Out 2"],
  "scenario": "가족들과 함께 보기 좋은"
}' "$ENDPOINT/recommendations"
```

# Cloud run
### Cloud run 에 배포
```
gcloud run deploy mr-run \
--image ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/movie-recommendation  \
--region ${REGION}  \
--set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},GEMINI_MODEL=${GEMINI_MODEL} \
--service-account ${GCP_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com  \
--allow-unauthenticated
```

### 테스트
```
export ENDPOINT=[Endpoint of Cloud Run Service]

curl -X POST -H "Content-Type: application/json" -d '{
  "movies": ["Despicable Me 4", "Inside Out 2"],
  "scenario": "가족들과 함께 보기 좋은"
}' "$ENDPOINT/recommendations"
```
