# DevSecOps Workshop — Container backdoor: detect & remediate

> Demuestra cómo un **security gate** con Trivy en CodePipeline impide que una imagen con backdoor llegue a ECR — y cómo remediarla para que el deploy fluya.

## Stack

| Capa | Herramienta |
|---|---|
| Source | **GitHub** (vía CodeStar Connection) |
| Pipeline | **AWS CodePipeline** |
| Build & Scan | **AWS CodeBuild** + **Trivy** (Aqua, open source) |
| Registry | **Amazon ECR** (con scan-on-push de Inspector v2) |
| Container | **Docker** multi-stage |

## Estructura del repo

```
devsecops-workshop/
├── README.md                    ← este archivo (overview)
├── buildspec.yml                ← pipeline: trivy → docker build → trivy → push
├── app/                         ← microservicio Flask de demo
│   ├── app.py
│   └── requirements.txt
├── vulnerable/
│   └── Dockerfile               ← ❌ SSH backdoor + creds + CVEs
├── secure/
│   └── Dockerfile               ← ✅ multi-stage, USER appuser, sin secretos
├── trivy/
│   ├── trivy.yaml               ← config global
│   └── .trivyignore             ← excepciones documentadas
├── infrastructure/
│   ├── 01-ecr.yaml              ← CloudFormation: repo ECR + scan-on-push
│   └── 02-pipeline.yaml         ← CloudFormation: CodePipeline + CodeBuild + IAM
└── docs/
    └── lab-guide.md             ← ⭐ guía paso a paso del workshop
```

## Flujo del pipeline

```
GitHub push
   │
   ▼
CodePipeline ── Source ───────────► CodeBuild (Trivy security gate)
                                         │
                                         ├─ trivy config  Dockerfile     ┐
                                         ├─ trivy fs --scanners secret   ├─► HIGH/CRITICAL?
                                         ├─ docker build                 │     │
                                         └─ trivy image                  ┘     │
                                                                               ▼
                                                              ┌──────────────┴──────────────┐
                                                              │                             │
                                                              ▼                             ▼
                                                          FAIL build                  docker push
                                                          (no llega a ECR)                  │
                                                                                            ▼
                                                                                          ECR
                                                                                            │
                                                                                            ▼
                                                                                  Inspector v2 (post-push)
```

## Backdoor que vamos a demostrar

El `vulnerable/Dockerfile` contiene 6 issues de seguridad reales:

1. Imagen base `python:3.7.4-alpine3.10` (CVEs HIGH/CRITICAL conocidos).
2. Variables de entorno con credenciales AWS y tokens de GitHub hardcodeados.
3. Password de `root` fijo (`Admin123!`).
4. Usuario oculto `devops` con sudo NOPASSWD y password débil.
5. SSH server expuesto y configurado para permitir `PermitRootLogin yes` + `PermitEmptyPasswords yes`.
6. Contenedor corriendo como root, puerto 22 expuesto, sshd como proceso principal.

Cada uno de esos issues mapea a una categoría que Trivy detecta:

| # | Issue | Detectado por |
|---|---|---|
| 1 | CVEs en imagen base | `trivy image --scanners vuln` |
| 2 | Secretos hardcodeados | `trivy fs --scanners secret` y `trivy image --scanners secret` |
| 3-4 | Password fijos | code review + policy custom (referenciado en lab-guide) |
| 5-6 | Misconfig de Dockerfile | `trivy config` |

## Empezar

Sigue [`docs/lab-guide.md`](docs/lab-guide.md) — está pensado para ejecutarse en vivo durante el workshop.

## Discusión post-demo

- **Defense in depth:** Trivy en CI no reemplaza Inspector v2 en ECR ni los admission controllers en EKS. Cada uno cubre un momento distinto del SDLC.
- **Shift-left real:** mismo escaneo se puede correr en `pre-commit` localmente (ver Apéndice A del lab-guide).
- **Excepciones gobernadas:** `.trivyignore` se commitea y se revisa en PR — nunca decisiones unilaterales.
- **Próximos pasos:** integrar reportes a **AWS Security Hub** vía `aws securityhub batch-import-findings` desde el buildspec.
