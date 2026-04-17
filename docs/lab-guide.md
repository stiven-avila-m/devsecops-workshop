# Lab Guide — Workshop DevSecOps

**Detección y remediación de un backdoor en un contenedor antes de llegar a ECR.**

## Objetivo

Al terminar este lab los asistentes podrán:

1. Identificar **patrones de backdoor** en un Dockerfile (credenciales hardcodeadas + SSH server expuesto).
2. Integrar **Trivy** como *security gate* dentro de un pipeline CI/CD en AWS.
3. Demostrar cómo el pipeline **bloquea** la imagen antes de que llegue a ECR.
4. Aplicar la **remediación** y confirmar que el deploy fluye end-to-end.

**Duración estimada:** 60–75 minutos.

## Pre-requisitos

- Cuenta AWS con permisos para crear: ECR, CodePipeline, CodeBuild, IAM, S3, CodeStar Connections.
- AWS CLI v2 configurado (`aws sts get-caller-identity` debe responder).
- Docker instalado localmente (para validar antes de pushear).
- Cuenta de GitHub y un repo nuevo vacío llamado `devsecops-workshop`.
- Trivy local opcional (para que los asistentes prueben el escaneo en su laptop).

```bash
brew install trivy
sudo apt-get install trivy
```

## Paso 0 — Preparar el repo

```bash
https://github.com/stiven-avila-m/devsecops-workshop.git
cd devsecops-workshop
```

> **Importante:** el `buildspec.yml` viene apuntando a `vulnerable/Dockerfile` por defecto. Esto es a propósito para la primera demo.


## Paso 1 — Crear la conexión CodeStar a GitHub

```bash
aws codestar-connections create-connection --provider-type GitHub --connection-name devsecops-workshop-conn --profile itera
```

> Anota el ARN. Luego ve a la consola → Developer Tools → Settings → Connections → **Update pending connection** y autoriza GitHub. Sin este paso el pipeline no puede leer el repo.


## Paso 2 — Crear ECR

```bash
aws cloudformation deploy --stack-name devsecops-ecr -template-file infrastructure/01-ecr.yaml --capabilities CAPABILITY_NAMED_IAM --profile itera
```

Verifica:

```bash
aws ecr describe-repositories --repository-names devsecops-demo --profile itera
```


## Paso 3 — Crear el pipeline

```bash
aws cloudformation deploy -stack-name devsecops-pipeline --template-file infrastructure/02-pipeline.yaml --capabilities CAPABILITY_NAMED_IAM --parameter-overrides GitHubOwner=stiven-avila-m CodeStarConnectionArn=<arn-del-paso-1>
```

Esto crea: bucket S3 de artefactos, roles IAM, CodeBuild project y CodePipeline.


## Paso 4 — DEMO 1: el pipeline detecta el backdoor

El primer push (que ya hiciste en el Paso 0) dispara el pipeline. Abre la consola:

```
CodePipeline → devsecops-workshop-pipeline → View pipeline
```

Verás dos stages:

1. **Source** ✓ — descarga el repo desde GitHub.
2. **SecurityScanAndBuild** ✗ — **falla**.

Click en **View logs** del stage de build. Busca estas secciones:

### 4.1 — Trivy config sobre el Dockerfile

```
Type: Dockerfile
DS002 (HIGH):  Specify at least 1 USER command
DS013 (HIGH):  'sshd' should not run as PID 1
AVD-DS-0001:   ":latest" tag used (versionado)
```

### 4.2 — Trivy fs (secret scanner)

```
HIGH: AWS Access Key ID detected (vulnerable/Dockerfile:21)
HIGH: AWS Secret Access Key detected (vulnerable/Dockerfile:22)
HIGH: GitHub Personal Access Token (vulnerable/Dockerfile:24)
```

### 4.3 — Trivy image (CVEs sobre la imagen ya construida)

```
python:3.7.4-alpine3.10 (alpine 3.10.x)
============================================
Total: 47 (HIGH: 31, CRITICAL: 16)

CVE-2021-3711   openssl   CRITICAL
CVE-2022-37434  zlib      CRITICAL
...
```

### 4.4 — El gate

```
================================================================
BUILD FALLO: Trivy detecto vulnerabilidades en la IMAGEN.
La imagen NO sera publicada a ECR.
================================================================
```

**Confirma que ECR está vacío:**

```bash
aws ecr list-images --repository-name devsecops-demo --profile itera
# {"imageIds": []}   ← perfecto, el gate funcionó
```

**Punto pedagógico:** explica al público que esa imagen, si hubiera llegado a producción, expondría:

- Login SSH como `root` con password `Admin123!`.
- Usuario `devops` con sudo NOPASSWD y password `devops`.
- Credenciales AWS reales (en el ejemplo son ficticias) accesibles vía `env` desde dentro del contenedor.
- 47 CVEs explotables.


## Paso 5 — DEMO 2: remediar y volver a desplegar

Edita `buildspec.yml` y cambia:

```yaml
DOCKERFILE_PATH: "vulnerable/Dockerfile"
```

por:

```yaml
DOCKERFILE_PATH: "secure/Dockerfile"
```

Commit + push:

```bash
git add buildspec.yml
git commit -m "fix(security): usar Dockerfile remediado"
git push
```

El pipeline arranca solo. Esta vez:

- `trivy config` → `0 misconfigurations`
- `trivy fs --scanners secret` → `0 secrets`
- `trivy image` → `0 HIGH, 0 CRITICAL` (puede haber LOW/MEDIUM, no rompen)
- `docker push` ejecuta y la imagen aparece en ECR.

```bash
aws ecr list-images --repository-name devsecops-demo --profile itera
# {"imageIds": [{"imageDigest": "sha256:...", "imageTag": "latest"}]}
```


## Paso 6 — Discusión guiada (10 min)

Preguntas para el grupo:

1. ¿Qué pasa si un dev añade `# trivy:ignore:CVE-2022-37434` para hacer pasar el build? → mostrar `.trivyignore` y la conversación que debe dispararse en code review.
2. ¿Por qué `trivy config` además de `trivy image`? → atrapan capas distintas (estática vs dinámica).
3. ¿Dónde encaja **Amazon Inspector v2**? → defensa en profundidad: incluso si algo se cuela al ECR, Inspector lo escanea on-push y publica a Security Hub.
4. ¿Cómo se traduce esto a Kubernetes/EKS? → mismo Trivy + admission controllers (Kyverno, OPA Gatekeeper, Trivy Operator).


## Paso 7 — Limpieza

```bash
aws cloudformation delete-stack --stack-name devsecops-pipeline --profile itera
aws ecr delete-repository --repository-name devsecops-demo --force --profile itera
aws cloudformation delete-stack --stack-name devsecops-ecr --profile itera
aws codestar-connections delete-connection --connection-arn <arn> --profile itera
```


## Apéndice A — Probar Trivy localmente (sin pipeline)

```bash
# 1. Misconfig del Dockerfile
trivy config vulnerable/Dockerfile

# 2. Secretos en todo el repo
trivy fs --scanners secret .

# 3. Build local + scan de la imagen
docker build -f vulnerable/Dockerfile -t demo:vuln .
trivy image --severity HIGH,CRITICAL demo:vuln
```

## Apéndice B — Output esperado del scanner (resumen)

| Hallazgo                                   | Tipo Trivy   | Severidad |
|
| `python:3.7.4-alpine3.10` con CVEs        | `vuln`       | CRITICAL  |
| `AWS_ACCESS_KEY_ID=AKIA…`                  | `secret`     | HIGH      |
| `AWS_SECRET_ACCESS_KEY=…`                  | `secret`     | HIGH      |
| `API_TOKEN=ghp_…`                          | `secret`     | HIGH      |
| Falta directiva `USER` (corre como root)   | `misconfig`  | HIGH      |
| Puerto 22 expuesto                         | `misconfig`  | MEDIUM    |
| `sshd` como ENTRYPOINT (servicio extra)    | `misconfig`  | HIGH      |
| `chpasswd` con password fijo               | revisado en code-review / `--config-policy` custom | HIGH |