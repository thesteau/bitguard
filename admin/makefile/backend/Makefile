start:
	cd /home/ubuntu/api && docker compose pull && \
	docker compose up -d --build && \
        cd /home/ubuntu/database && docker compose pull && \
        docker compose up -d --build

down:
	cd /home/ubuntu/api && \
        docker compose down && \
        cd /home/ubuntu/database && \
        docker compose down