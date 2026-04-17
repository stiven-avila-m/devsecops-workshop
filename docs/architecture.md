# Diagrama de arquitectura

Pega esto en cualquier renderer Mermaid (GitHub lo renderiza nativamente).

```mermaid
flowchart LR
    Dev([Developer]) -->|git push| GH[(GitHub repo)]
    GH -->|webhook<br/>CodeStar Connection| CP[CodePipeline]

    subgraph CB[CodeBuild · buildspec.yml]
        direction TB
        T1[trivy config<br/>Dockerfile misconfig]
        T2[trivy fs<br/>--scanners secret]
        BUILD[docker build]
        T3[trivy image<br/>--scanners vuln,secret,misconfig]
        GATE{HIGH o<br/>CRITICAL?}
        PUSH[docker push a ECR]

        T1 --> T2 --> BUILD --> T3 --> GATE
        GATE -- No --> PUSH
        GATE -- Si --> FAIL((BUILD FAIL<br/>imagen NO publicada))
    end

    CP --> CB
    PUSH --> ECR[(Amazon ECR)]
    ECR -->|scan-on-push| INS[Amazon Inspector v2]
    INS --> SH[Security Hub]

    classDef fail fill:#ff6b6b,stroke:#c92a2a,color:#fff
    classDef ok fill:#51cf66,stroke:#2f9e44,color:#fff
    class FAIL fail
    class PUSH,ECR ok
```

## Mapeo de la cadena de defensa

```
TIEMPO ──────────────────────────────────────────────────────►
 │
 ├─ pre-commit (opcional)    trivy config / trivy fs local
 │
 ├─ CI (CodePipeline)        trivy config + trivy fs + trivy image  ← ★ workshop
 │                           (security gate: bloquea push a ECR)
 │
 ├─ Registry (ECR)           Inspector v2 scan-on-push + continuous
 │                           findings -> Security Hub -> EventBridge
 │
 ├─ Admission (EKS)          Trivy Operator / Kyverno / OPA Gatekeeper
 │                           valida la imagen antes del Pod admission
 │
 └─ Runtime                  Falco / GuardDuty Runtime Monitoring
                             detecta comportamiento anomalo (ej. nc reverse shell)
```

## Decisiones clave

- **Por qué Trivy en CodeBuild y no Inspector solo:** Inspector funciona *después* del push. Trivy en CodeBuild es el primer punto donde podemos rechazar la imagen sin dejar artefactos en el registry. Defense in depth: usamos los dos.
- **Por qué `--ignore-unfixed` en `trivy image`:** evita ruido por CVEs sin parche disponible. Para el workshop lo dejamos activo; en proyectos reales se evalúa por tipo de carga.
- **Por qué `IMAGE_TAG = git-sha`:** cada imagen es trazable a un commit. Combinado con `ImageTagMutability: IMMUTABLE` en ECR garantiza que `latest` no se sobrescribe accidentalmente con algo viejo.
