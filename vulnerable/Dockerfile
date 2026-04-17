# =============================================================================
#  DevSecOps Workshop - Dockerfile VULNERABLE (NO USAR EN PRODUCCION)
# =============================================================================
#  Este Dockerfile contiene MULTIPLES problemas de seguridad disenados para
#  ser detectados por Trivy durante el pipeline:
#
#   [1] Imagen base obsoleta con CVEs HIGH/CRITICAL  -> trivy image (vuln)
#   [2] Credenciales AWS hardcodeadas en ENV         -> trivy image (secret)
#   [3] Usuario root con password fijo (backdoor)    -> trivy config (misconfig)
#   [4] Servidor SSH expuesto como ENTRYPOINT        -> trivy config (misconfig)
#   [5] Contenedor corre como root (sin USER)        -> trivy config (misconfig)
#   [6] Puerto 22 expuesto                           -> trivy config (misconfig)
# =============================================================================

# [1] Imagen base intencionalmente vieja con CVEs conocidos
FROM python:3.7.4-alpine3.10

LABEL maintainer="devsecops-workshop"
LABEL description="VULNERABLE container for DevSecOps demo - DO NOT DEPLOY"

# [2] Secretos hardcodeados (Trivy secret scanner los detecta)
ENV AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
ENV AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
ENV DB_PASSWORD=SuperSecret123!
ENV API_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz12

# Instalar SSH server (BACKDOOR)
RUN apk add --no-cache openssh bash sudo

# [3] BACKDOOR: usuario root con password conocido
RUN echo 'root:Admin123!' | chpasswd

# [3b] BACKDOOR: usuario oculto con privilegios sudo y password debil
RUN adduser -D -s /bin/bash devops \
    && echo 'devops:devops' | chpasswd \
    && echo 'devops ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# [4] Configurar sshd para permitir login root remoto (mala practica grave)
RUN ssh-keygen -A \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PermitEmptyPasswords no/PermitEmptyPasswords yes/' /etc/ssh/sshd_config

WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .

# [6] Exponer puerto SSH (backdoor accesible)
EXPOSE 22
EXPOSE 8080

# [5] Sin directiva USER -> corre como root
# [4] ENTRYPOINT levanta sshd en background + la app
#     Esto hace que el contenedor escuche conexiones SSH en runtime
CMD ["/bin/sh", "-c", "/usr/sbin/sshd && python app.py"]
