FROM php:8.2-cli-alpine

RUN apk add --no-cache \
    bash curl git zip unzip \
    libzip-dev oniguruma-dev \
    sqlite sqlite-dev \
    && docker-php-ext-install pdo pdo_mysql pdo_sqlite zip bcmath

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/app

COPY . .

RUN mkdir -p bootstrap/cache storage/logs storage/framework/cache storage/framework/sessions storage/framework/views \
    && chmod -R 775 storage bootstrap/cache

RUN if [ -f composer.json ]; then \
    composer install --no-interaction --no-scripts; \
    fi

RUN mkdir -p database && touch database/coupons.sqlite

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
