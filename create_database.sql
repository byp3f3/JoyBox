-- ============================================================
-- Скрипт создания базы данных JoyBox
-- Запустите этот скрипт в pgAdmin для создания всех таблиц
-- ============================================================

-- 1. Создание базы данных (выполнить отдельно в pgAdmin)
-- CREATE DATABASE joybox;

-- После создания базы данных подключитесь к ней и выполните остальной скрипт

-- ============================================================
-- ТАБЛИЦЫ ПРИЛОЖЕНИЯ
-- ============================================================

-- Таблица ролей
CREATE TABLE "role" (
    "roleId" SERIAL PRIMARY KEY,
    "roleName" VARCHAR(100) NOT NULL
);

-- Таблица пользователей (включает поля Django AbstractUser)
CREATE TABLE "user" (
    "userId" BIGSERIAL PRIMARY KEY,
    "password" VARCHAR(100) NOT NULL,
    "last_login" TIMESTAMP WITH TIME ZONE NULL,
    "is_superuser" BOOLEAN NOT NULL DEFAULT FALSE,
    "username" VARCHAR(150) NOT NULL,
    "first_name" VARCHAR(150) NOT NULL DEFAULT '',
    "last_name" VARCHAR(150) NOT NULL DEFAULT '',
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "is_staff" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "date_joined" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "lastName" VARCHAR(100) NOT NULL,
    "firstName" VARCHAR(100) NOT NULL,
    "middleName" VARCHAR(100) NULL,
    "roleId" INTEGER NOT NULL,
    "phone" VARCHAR(11) NOT NULL,
    "birthDate" DATE NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT "user_roleId_fk" FOREIGN KEY ("roleId")
        REFERENCES "role" ("roleId") ON DELETE CASCADE
);

CREATE INDEX "user_roleId_idx" ON "user" ("roleId");
CREATE INDEX "user_email_idx" ON "user" ("email");

-- Таблица категорий
CREATE TABLE "category" (
    "categoryId" SERIAL PRIMARY KEY,
    "categoryName" VARCHAR(100) NOT NULL,
    "categoryDescription" TEXT NOT NULL
);

-- Таблица брендов
CREATE TABLE "brand" (
    "brandId" SERIAL PRIMARY KEY,
    "brandName" VARCHAR(100) NOT NULL,
    "brandDescription" TEXT NOT NULL,
    "brandCountry" VARCHAR(100) NOT NULL
);

-- Таблица продуктов
CREATE TABLE "product" (
    "productId" BIGSERIAL PRIMARY KEY,
    "productName" VARCHAR(100) NOT NULL,
    "productDescription" TEXT NOT NULL,
    "categoryId" INTEGER NOT NULL,
    "brandId" INTEGER NOT NULL,
    "price" NUMERIC(10, 2) NOT NULL,
    "ageRating" INTEGER NOT NULL,
    "quantity" INTEGER NOT NULL,
    "weightKg" NUMERIC(10, 2) NOT NULL,
    "dimensions" VARCHAR(50) NOT NULL,
    CONSTRAINT "product_categoryId_fk" FOREIGN KEY ("categoryId")
        REFERENCES "category" ("categoryId") ON DELETE CASCADE,
    CONSTRAINT "product_brandId_fk" FOREIGN KEY ("brandId")
        REFERENCES "brand" ("brandId") ON DELETE CASCADE
);

CREATE INDEX "product_categoryId_idx" ON "product" ("categoryId");
CREATE INDEX "product_brandId_idx" ON "product" ("brandId");

-- Таблица изображений продуктов
CREATE TABLE "productImage" (
    "productImageId" BIGSERIAL PRIMARY KEY,
    "productId" BIGINT NOT NULL,
    "url" VARCHAR(500) NOT NULL,
    "altText" VARCHAR(100) NOT NULL,
    "isMain" BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT "productImage_productId_fk" FOREIGN KEY ("productId")
        REFERENCES "product" ("productId") ON DELETE CASCADE
);

CREATE INDEX "productImage_productId_idx" ON "productImage" ("productId");

-- Таблица атрибутов продуктов
CREATE TABLE "productAttribute" (
    "productAttributeId" BIGSERIAL PRIMARY KEY,
    "productId" BIGINT NOT NULL,
    "productAttributeName" VARCHAR(100) NOT NULL,
    "productAttributeValue" VARCHAR(100) NOT NULL,
    "productAttributeUnit" VARCHAR(50) NULL,
    CONSTRAINT "productAttribute_productId_fk" FOREIGN KEY ("productId")
        REFERENCES "product" ("productId") ON DELETE CASCADE
);

CREATE INDEX "productAttribute_productId_idx" ON "productAttribute" ("productId");

-- Таблица адресов
CREATE TABLE "address" (
    "addressId" BIGSERIAL PRIMARY KEY,
    "userId" BIGINT NOT NULL,
    "city" VARCHAR(100) NOT NULL,
    "street" VARCHAR(100) NOT NULL,
    "house" VARCHAR(50) NOT NULL,
    "flat" VARCHAR(10) NULL,
    "index" VARCHAR(6) NOT NULL,
    CONSTRAINT "address_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE
);

CREATE INDEX "address_userId_idx" ON "address" ("userId");

-- Таблица статусов заказов
CREATE TABLE "orderStatus" (
    "orderStatusId" SERIAL PRIMARY KEY,
    "orderStatusName" VARCHAR(100) NOT NULL
);

-- Таблица заказов
CREATE TABLE "order" (
    "orderId" BIGSERIAL PRIMARY KEY,
    "userId" BIGINT NOT NULL,
    "orderStatusId" INTEGER NOT NULL,
    "total" NUMERIC(10, 2) NOT NULL,
    "addressId" BIGINT NOT NULL,
    "deliveryType" VARCHAR(20) NOT NULL,
    "paymentType" VARCHAR(30) NOT NULL,
    "paymentStatus" VARCHAR(30) NOT NULL,
    "note" VARCHAR(100) NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT "order_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE,
    CONSTRAINT "order_orderStatusId_fk" FOREIGN KEY ("orderStatusId")
        REFERENCES "orderStatus" ("orderStatusId") ON DELETE CASCADE,
    CONSTRAINT "order_addressId_fk" FOREIGN KEY ("addressId")
        REFERENCES "address" ("addressId") ON DELETE CASCADE
);

CREATE INDEX "order_userId_idx" ON "order" ("userId");
CREATE INDEX "order_orderStatusId_idx" ON "order" ("orderStatusId");
CREATE INDEX "order_addressId_idx" ON "order" ("addressId");

-- Таблица позиций заказа
CREATE TABLE "orderItem" (
    "orderItemId" BIGSERIAL PRIMARY KEY,
    "orderId" BIGINT NOT NULL,
    "productId" BIGINT NOT NULL,
    "quantity" INTEGER NOT NULL,
    "unitPrice" NUMERIC(10, 2) NOT NULL,
    CONSTRAINT "orderItem_orderId_fk" FOREIGN KEY ("orderId")
        REFERENCES "order" ("orderId") ON DELETE CASCADE,
    CONSTRAINT "orderItem_productId_fk" FOREIGN KEY ("productId")
        REFERENCES "product" ("productId") ON DELETE CASCADE
);

CREATE INDEX "orderItem_orderId_idx" ON "orderItem" ("orderId");
CREATE INDEX "orderItem_productId_idx" ON "orderItem" ("productId");

-- Таблица отзывов
CREATE TABLE "review" (
    "reviewId" BIGSERIAL PRIMARY KEY,
    "productId" BIGINT NOT NULL,
    "userId" BIGINT NOT NULL,
    "rating" INTEGER NOT NULL,
    "reviewText" TEXT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT "review_productId_fk" FOREIGN KEY ("productId")
        REFERENCES "product" ("productId") ON DELETE CASCADE,
    CONSTRAINT "review_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE
);

CREATE INDEX "review_productId_idx" ON "review" ("productId");
CREATE INDEX "review_userId_idx" ON "review" ("userId");

-- Таблица списка желаний
CREATE TABLE "wishlist" (
    "wishlistId" BIGSERIAL PRIMARY KEY,
    "userId" BIGINT NOT NULL,
    "productId" BIGINT NOT NULL,
    CONSTRAINT "wishlist_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE,
    CONSTRAINT "wishlist_productId_fk" FOREIGN KEY ("productId")
        REFERENCES "product" ("productId") ON DELETE CASCADE
);

CREATE INDEX "wishlist_userId_idx" ON "wishlist" ("userId");
CREATE INDEX "wishlist_productId_idx" ON "wishlist" ("productId");

-- Таблица корзины
CREATE TABLE "cart" (
    "cartId" BIGSERIAL PRIMARY KEY,
    "userId" BIGINT NOT NULL,
    "productId" BIGINT NOT NULL,
    "quantity" INTEGER NOT NULL,
    CONSTRAINT "cart_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE,
    CONSTRAINT "cart_productId_fk" FOREIGN KEY ("productId")
        REFERENCES "product" ("productId") ON DELETE CASCADE
);

CREATE INDEX "cart_userId_idx" ON "cart" ("userId");
CREATE INDEX "cart_productId_idx" ON "cart" ("productId");

-- Таблица связей родитель-ребенок
CREATE TABLE "parentChild" (
    "parentChildId" BIGSERIAL PRIMARY KEY,
    "userId" BIGINT NOT NULL,
    "childId" BIGINT NOT NULL,
    CONSTRAINT "parentChild_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE,
    CONSTRAINT "parentChild_childId_fk" FOREIGN KEY ("childId")
        REFERENCES "user" ("userId") ON DELETE CASCADE
);

CREATE INDEX "parentChild_userId_idx" ON "parentChild" ("userId");
CREATE INDEX "parentChild_childId_idx" ON "parentChild" ("childId");

-- Таблица журнала аудита
CREATE TABLE "auditLog" (
    "auditLogId" BIGSERIAL PRIMARY KEY,
    "userId" BIGINT NOT NULL,
    "action" VARCHAR(100) NOT NULL,
    "tableName" VARCHAR(100) NOT NULL,
    "recordId" BIGINT NOT NULL,
    "oldValues" JSONB NULL,
    "newValues" JSONB NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT "auditLog_userId_fk" FOREIGN KEY ("userId")
        REFERENCES "user" ("userId") ON DELETE CASCADE
);

CREATE INDEX "auditLog_userId_idx" ON "auditLog" ("userId");

-- ============================================================
-- СВЯЗУЮЩИЕ ТАБЛИЦЫ (Many-to-Many для Django-авторизации)
-- ============================================================

-- Таблица связи пользователь-группы (Django auth)
CREATE TABLE "user_groups" (
    "id" BIGSERIAL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "group_id" INTEGER NOT NULL,
    UNIQUE ("user_id", "group_id"),
    CONSTRAINT "user_groups_user_id_fk" FOREIGN KEY ("user_id")
        REFERENCES "user" ("userId") ON DELETE CASCADE
);

CREATE INDEX "user_groups_user_id_idx" ON "user_groups" ("user_id");
CREATE INDEX "user_groups_group_id_idx" ON "user_groups" ("group_id");

-- Таблица связи пользователь-разрешения (Django auth)
CREATE TABLE "user_user_permissions" (
    "id" BIGSERIAL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "permission_id" INTEGER NOT NULL,
    UNIQUE ("user_id", "permission_id"),
    CONSTRAINT "user_user_permissions_user_id_fk" FOREIGN KEY ("user_id")
        REFERENCES "user" ("userId") ON DELETE CASCADE
);

CREATE INDEX "user_user_permissions_user_id_idx" ON "user_user_permissions" ("user_id");
CREATE INDEX "user_user_permissions_permission_id_idx" ON "user_user_permissions" ("permission_id");

-- ============================================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ============================================================

-- Роли пользователей
INSERT INTO "role" ("roleId", "roleName") VALUES
    (1, 'Покупатель'),
    (2, 'Ребенок'),
    (3, 'Менеджер'),
    (4, 'Администратор');

-- Сброс последовательности для roleId
SELECT setval('"role_roleId_seq"', (SELECT MAX("roleId") FROM "role"));

-- Статусы заказов
INSERT INTO "orderStatus" ("orderStatusId", "orderStatusName") VALUES
    (1, 'Новый'),
    (2, 'В обработке'),
    (3, 'Отправлен'),
    (4, 'Доставлен'),
    (5, 'Отменен');

-- Сброс последовательности для orderStatusId
SELECT setval('"orderStatus_orderStatusId_seq"', (SELECT MAX("orderStatusId") FROM "orderStatus"));

-- ============================================================
-- ОГРАНИЧЕНИЯ ЦЕЛОСТНОСТИ (CHECK, UNIQUE)
-- ============================================================

-- Рейтинг отзыва: от 1 до 5
ALTER TABLE "review"
    ADD CONSTRAINT "review_rating_check" CHECK ("rating" BETWEEN 1 AND 5);

-- Один пользователь — один отзыв на товар (UNIQUE)
ALTER TABLE "review"
    ADD CONSTRAINT "review_user_product_unique" UNIQUE ("userId", "productId");

-- Цена товара > 0
ALTER TABLE "product"
    ADD CONSTRAINT "product_price_check" CHECK ("price" > 0);

-- Количество товара на складе >= 0
ALTER TABLE "product"
    ADD CONSTRAINT "product_quantity_check" CHECK ("quantity" >= 0);

-- Вес товара > 0
ALTER TABLE "product"
    ADD CONSTRAINT "product_weightKg_check" CHECK ("weightKg" > 0);

-- Возрастной рейтинг >= 0
ALTER TABLE "product"
    ADD CONSTRAINT "product_ageRating_check" CHECK ("ageRating" >= 0);

-- Количество в позиции заказа > 0
ALTER TABLE "orderItem"
    ADD CONSTRAINT "orderItem_quantity_check" CHECK ("quantity" > 0);

-- Цена за единицу в позиции заказа > 0
ALTER TABLE "orderItem"
    ADD CONSTRAINT "orderItem_unitPrice_check" CHECK ("unitPrice" > 0);

-- Итого заказа >= 0
ALTER TABLE "order"
    ADD CONSTRAINT "order_total_check" CHECK ("total" >= 0);

-- Допустимые типы доставки
ALTER TABLE "order"
    ADD CONSTRAINT "order_deliveryType_check"
    CHECK ("deliveryType" IN ('самовывоз', 'пункт выдачи', 'курьером'));

-- Допустимые типы оплаты
ALTER TABLE "order"
    ADD CONSTRAINT "order_paymentType_check"
    CHECK ("paymentType" IN ('онлайн', 'картой при получении', 'наличными при получении'));

-- Допустимые статусы оплаты
ALTER TABLE "order"
    ADD CONSTRAINT "order_paymentStatus_check"
    CHECK ("paymentStatus" IN ('ждет оплаты', 'оплачено', 'возврат средств', 'средства возвращены'));

-- Количество товара в корзине > 0
ALTER TABLE "cart"
    ADD CONSTRAINT "cart_quantity_check" CHECK ("quantity" > 0);

-- Один товар в корзине пользователя один раз (UNIQUE)
ALTER TABLE "cart"
    ADD CONSTRAINT "cart_user_product_unique" UNIQUE ("userId", "productId");

-- Один товар в избранном пользователя один раз (UNIQUE)
ALTER TABLE "wishlist"
    ADD CONSTRAINT "wishlist_user_product_unique" UNIQUE ("userId", "productId");

-- Формат телефона: ровно 11 цифр
ALTER TABLE "user"
    ADD CONSTRAINT "user_phone_check" CHECK ("phone" ~ '^[0-9]{11}$');

-- Формат почтового индекса: ровно 6 цифр
ALTER TABLE "address"
    ADD CONSTRAINT "address_index_check" CHECK ("index" ~ '^[0-9]{6}$');

-- Ребёнок может иметь только одного родителя (связь 1:1 по childId)
ALTER TABLE "parentChild"
    ADD CONSTRAINT "parentChild_childId_unique" UNIQUE ("childId");

-- Допустимые действия аудита
ALTER TABLE "auditLog"
    ADD CONSTRAINT "auditLog_action_check"
    CHECK ("action" IN ('CREATE', 'UPDATE', 'DELETE'));

-- ============================================================
-- ПРЕДСТАВЛЕНИЯ (VIEW) для отчётности
-- ============================================================

-- 1. Каталог товаров с категорией, брендом и средним рейтингом
CREATE OR REPLACE VIEW v_product_catalog AS
SELECT
    p."productId",
    p."productName",
    p."price",
    p."quantity"                                         AS "stockQuantity",
    p."ageRating",
    c."categoryName",
    b."brandName",
    b."brandCountry",
    COALESCE(ROUND(AVG(r."rating"), 2), 0)               AS "avgRating",
    COUNT(r."reviewId")                                   AS "reviewCount"
FROM "product" p
    JOIN "category" c ON p."categoryId" = c."categoryId"
    JOIN "brand"    b ON p."brandId"    = b."brandId"
    LEFT JOIN "review" r ON p."productId" = r."productId"
GROUP BY p."productId", p."productName", p."price", p."quantity",
         p."ageRating", c."categoryName", b."brandName", b."brandCountry";

-- 2. Детали заказов — заказ, покупатель, статус, позиции
CREATE OR REPLACE VIEW v_order_details AS
SELECT
    o."orderId",
    u."firstName" || ' ' || u."lastName"                  AS "customerName",
    u."email"                                             AS "customerEmail",
    os."orderStatusName"                                  AS "status",
    o."deliveryType",
    o."paymentType",
    o."paymentStatus",
    o."total",
    o."createdAt"                                         AS "orderDate",
    oi."orderItemId",
    p."productName",
    oi."quantity",
    oi."unitPrice",
    (oi."quantity" * oi."unitPrice")                       AS "lineTotal"
FROM "order" o
    JOIN "user"        u  ON o."userId"        = u."userId"
    JOIN "orderStatus" os ON o."orderStatusId"  = os."orderStatusId"
    JOIN "orderItem"   oi ON o."orderId"        = oi."orderId"
    JOIN "product"     p  ON oi."productId"     = p."productId";

-- 3. Отчёт по продажам — выручка и количество заказов по месяцам
CREATE OR REPLACE VIEW v_sales_report AS
SELECT
    DATE_TRUNC('month', o."createdAt")::DATE              AS "month",
    COUNT(DISTINCT o."orderId")                           AS "orderCount",
    SUM(o."total")                                        AS "revenue",
    ROUND(AVG(o."total"), 2)                              AS "avgOrderTotal"
FROM "order" o
    JOIN "orderStatus" os ON o."orderStatusId" = os."orderStatusId"
WHERE os."orderStatusName" <> 'Отменен'
GROUP BY DATE_TRUNC('month', o."createdAt")
ORDER BY "month" DESC;

-- 4. Активность пользователей — заказы, отзывы, общая сумма
CREATE OR REPLACE VIEW v_user_activity AS
SELECT
    u."userId",
    u."firstName" || ' ' || u."lastName"                  AS "fullName",
    u."email",
    r."roleName",
    COUNT(DISTINCT o."orderId")                           AS "orderCount",
    COALESCE(SUM(o."total"), 0)                           AS "totalSpent",
    COUNT(DISTINCT rev."reviewId")                        AS "reviewCount",
    u."createdAt"                                         AS "registeredAt"
FROM "user" u
    JOIN "role"   r   ON u."roleId"  = r."roleId"
    LEFT JOIN "order"  o   ON u."userId" = o."userId"
    LEFT JOIN "review" rev ON u."userId" = rev."userId"
GROUP BY u."userId", u."firstName", u."lastName", u."email",
         r."roleName", u."createdAt";

-- 5. Популярные товары — топ товаров по количеству продаж
CREATE OR REPLACE VIEW v_popular_products AS
SELECT
    p."productId",
    p."productName",
    c."categoryName",
    SUM(oi."quantity")                                    AS "totalSold",
    SUM(oi."quantity" * oi."unitPrice")                   AS "totalRevenue",
    COALESCE(ROUND(AVG(r."rating"), 2), 0)               AS "avgRating"
FROM "product" p
    JOIN "category"  c  ON p."categoryId" = c."categoryId"
    JOIN "orderItem" oi ON p."productId"  = oi."productId"
    JOIN "order"     o  ON oi."orderId"   = o."orderId"
    JOIN "orderStatus" os ON o."orderStatusId" = os."orderStatusId"
    LEFT JOIN "review" r ON p."productId" = r."productId"
WHERE os."orderStatusName" <> 'Отменен'
GROUP BY p."productId", p."productName", c."categoryName"
ORDER BY "totalSold" DESC;

-- ============================================================
-- ХРАНИМЫЕ ПРОЦЕДУРЫ (бизнес-операции)
-- ============================================================

-- 1. Оформление заказа из корзины
--    Переносит все позиции корзины пользователя в новый заказ,
--    уменьшает остатки на складе и очищает корзину.
CREATE OR REPLACE PROCEDURE sp_create_order_from_cart(
    p_user_id   BIGINT,
    p_address_id BIGINT,
    p_delivery_type VARCHAR(20),
    p_payment_type  VARCHAR(30)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id     BIGINT;
    v_total        NUMERIC(10,2) := 0;
    v_status_id    INTEGER;
    v_cart_item    RECORD;
    v_product_qty  INTEGER;
BEGIN
    -- Проверка: корзина не пуста
    IF NOT EXISTS (SELECT 1 FROM "cart" WHERE "userId" = p_user_id) THEN
        RAISE EXCEPTION 'Корзина пользователя пуста';
    END IF;

    -- Проверка наличия товаров на складе
    FOR v_cart_item IN
        SELECT c."productId", c."quantity", p."productName", p."quantity" AS "stock"
        FROM "cart" c
            JOIN "product" p ON c."productId" = p."productId"
        WHERE c."userId" = p_user_id
    LOOP
        IF v_cart_item."stock" < v_cart_item."quantity" THEN
            RAISE EXCEPTION 'Недостаточно товара "%" на складе (в наличии: %, запрошено: %)',
                v_cart_item."productName", v_cart_item."stock", v_cart_item."quantity";
        END IF;
    END LOOP;

    -- Получить статус «Новый»
    SELECT "orderStatusId" INTO v_status_id
    FROM "orderStatus" WHERE "orderStatusName" = 'Новый';

    -- Рассчитать итог
    SELECT SUM(c."quantity" * p."price") INTO v_total
    FROM "cart" c
        JOIN "product" p ON c."productId" = p."productId"
    WHERE c."userId" = p_user_id;

    -- Создать заказ
    INSERT INTO "order" ("userId", "orderStatusId", "total", "addressId",
                         "deliveryType", "paymentType", "paymentStatus", "createdAt")
    VALUES (p_user_id, v_status_id, v_total, p_address_id,
            p_delivery_type, p_payment_type, 'ждет оплаты', NOW())
    RETURNING "orderId" INTO v_order_id;

    -- Перенести позиции из корзины в заказ и уменьшить остатки
    FOR v_cart_item IN
        SELECT c."productId", c."quantity", p."price"
        FROM "cart" c
            JOIN "product" p ON c."productId" = p."productId"
        WHERE c."userId" = p_user_id
    LOOP
        INSERT INTO "orderItem" ("orderId", "productId", "quantity", "unitPrice")
        VALUES (v_order_id, v_cart_item."productId",
                v_cart_item."quantity", v_cart_item."price");

        UPDATE "product"
        SET "quantity" = "quantity" - v_cart_item."quantity"
        WHERE "productId" = v_cart_item."productId";
    END LOOP;

    -- Очистить корзину
    DELETE FROM "cart" WHERE "userId" = p_user_id;
END;
$$;

-- 2. Отмена заказа с возвратом товара на склад
--    Меняет статус заказа на «Отменен», возвращает товары на склад,
--    меняет статус оплаты на «возврат средств» если было оплачено.
CREATE OR REPLACE PROCEDURE sp_cancel_order(
    p_order_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status VARCHAR(100);
    v_payment_status VARCHAR(30);
    v_cancel_status_id INTEGER;
    v_item RECORD;
BEGIN
    -- Получить текущий статус заказа
    SELECT os."orderStatusName", o."paymentStatus"
    INTO v_current_status, v_payment_status
    FROM "order" o
        JOIN "orderStatus" os ON o."orderStatusId" = os."orderStatusId"
    WHERE o."orderId" = p_order_id;

    IF v_current_status IS NULL THEN
        RAISE EXCEPTION 'Заказ #% не найден', p_order_id;
    END IF;

    IF v_current_status = 'Отменен' THEN
        RAISE EXCEPTION 'Заказ #% уже отменён', p_order_id;
    END IF;

    IF v_current_status = 'Доставлен' THEN
        RAISE EXCEPTION 'Нельзя отменить доставленный заказ #%', p_order_id;
    END IF;

    -- Получить ID статуса «Отменен»
    SELECT "orderStatusId" INTO v_cancel_status_id
    FROM "orderStatus" WHERE "orderStatusName" = 'Отменен';

    -- Вернуть товары на склад
    FOR v_item IN
        SELECT "productId", "quantity"
        FROM "orderItem"
        WHERE "orderId" = p_order_id
    LOOP
        UPDATE "product"
        SET "quantity" = "quantity" + v_item."quantity"
        WHERE "productId" = v_item."productId";
    END LOOP;

    -- Обновить заказ
    UPDATE "order"
    SET "orderStatusId" = v_cancel_status_id,
        "paymentStatus" = CASE
            WHEN "paymentStatus" = 'оплачено' THEN 'возврат средств'
            ELSE "paymentStatus"
        END
    WHERE "orderId" = p_order_id;
END;
$$;

-- 3. Пакетный пересчёт цен по категории (скидка / наценка)
--    Применяет процентное изменение цены ко всем товарам указанной категории.
--    Положительное значение — наценка, отрицательное — скидка.
CREATE OR REPLACE PROCEDURE sp_adjust_prices_by_category(
    p_category_id     INTEGER,
    p_percent_change  NUMERIC(5,2)   -- например: -10.00 для скидки 10%
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_affected INTEGER;
BEGIN
    IF p_percent_change < -90 OR p_percent_change > 500 THEN
        RAISE EXCEPTION 'Процент изменения должен быть от -90%% до 500%%';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM "category" WHERE "categoryId" = p_category_id) THEN
        RAISE EXCEPTION 'Категория с ID = % не найдена', p_category_id;
    END IF;

    UPDATE "product"
    SET "price" = ROUND("price" * (1 + p_percent_change / 100.0), 2)
    WHERE "categoryId" = p_category_id;

    GET DIAGNOSTICS v_affected = ROW_COUNT;

    RAISE NOTICE 'Цены обновлены для % товаров в категории %', v_affected, p_category_id;
END;
$$;

-- ============================================================
-- ФУНКЦИИ И ТРИГГЕРЫ ДЛЯ АУДИТА
-- ============================================================

-- Универсальная функция аудита: записывает изменения в auditLog
CREATE OR REPLACE FUNCTION fn_audit_log()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_action     VARCHAR(100);
    v_record_id  BIGINT;
    v_user_id    BIGINT;
    v_old_values JSONB := NULL;
    v_new_values JSONB := NULL;
BEGIN
    -- Определить тип операции
    IF TG_OP = 'INSERT' THEN
        v_action := 'CREATE';
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'DELETE';
    END IF;

    -- Получить ID записи и значения
    IF TG_OP = 'DELETE' THEN
        v_old_values := to_jsonb(OLD);
        v_record_id  := 0;  -- будет перезаписан ниже для каждой таблицы
    ELSE
        v_new_values := to_jsonb(NEW);
    END IF;

    IF TG_OP IN ('UPDATE') THEN
        v_old_values := to_jsonb(OLD);
    END IF;

    -- Определить ID записи в зависимости от таблицы
    CASE TG_TABLE_NAME
        WHEN 'product' THEN
            v_record_id := COALESCE(NEW."productId", OLD."productId");
        WHEN 'order' THEN
            v_record_id := COALESCE(NEW."orderId", OLD."orderId");
        WHEN 'user' THEN
            v_record_id := COALESCE(NEW."userId", OLD."userId");
        ELSE
            v_record_id := 0;
    END CASE;

    -- Получить ID пользователя из сессии (устанавливается Django)
    BEGIN
        v_user_id := current_setting('app.current_user_id')::BIGINT;
    EXCEPTION WHEN OTHERS THEN
        -- Если переменная не установлена, пытаемся взять из записи
        IF TG_TABLE_NAME = 'order' THEN
            v_user_id := COALESCE(NEW."userId", OLD."userId");
        ELSIF TG_TABLE_NAME = 'user' THEN
            v_user_id := COALESCE(NEW."userId", OLD."userId");
        ELSE
            v_user_id := 1;  -- системный пользователь по умолчанию
        END IF;
    END;

    -- Записать в журнал аудита
    INSERT INTO "auditLog" ("userId", "action", "tableName", "recordId",
                            "oldValues", "newValues", "createdAt")
    VALUES (v_user_id, v_action, TG_TABLE_NAME, v_record_id,
            v_old_values, v_new_values, NOW());

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$;

-- Триггер аудита на таблицу product
CREATE TRIGGER trg_product_audit
    AFTER INSERT OR UPDATE OR DELETE ON "product"
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- Триггер аудита на таблицу order
CREATE TRIGGER trg_order_audit
    AFTER INSERT OR UPDATE OR DELETE ON "order"
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- Триггер аудита на таблицу user
CREATE TRIGGER trg_user_audit
    AFTER INSERT OR UPDATE OR DELETE ON "user"
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- Функция: автообновление поля updatedAt при изменении отзыва
CREATE OR REPLACE FUNCTION fn_review_update_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW."updatedAt" := NOW();
    RETURN NEW;
END;
$$;

-- Триггер автообновления updatedAt на таблицу review
CREATE TRIGGER trg_review_updated_at
    BEFORE UPDATE ON "review"
    FOR EACH ROW EXECUTE FUNCTION fn_review_update_timestamp();
