## Modelo Relacional Normalizado

### Tabla: `users`

*   **Nombre:** `users`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `username` (VARCHAR(255), NOT NULL, UNIQUE)
    *   `firstname` (VARCHAR(255), NULL)
    *   `lastname` (VARCHAR(255), NULL)
    *   `dob` (VARCHAR(255), NULL)
    *   `bio` (TEXT, NULL)
    *   `profile_pic` (VARCHAR(255), NULL)
    *   `password` (VARCHAR(255), NOT NULL)
    *   `lastLogin` (DATETIME, NULL)
    *   `developer` (BOOLEAN, NULL)
*   **Clave Primaria:** `_id`

### Tabla: `analytics`

*   **Nombre:** `analytics`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `name` (VARCHAR(255), NOT NULL, UNIQUE)
*   **Clave Primaria:** `_id`

### Tabla: `analytics_stats`

*   **Nombre:** `analytics_stats`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `analytics_id` (INT, NOT NULL, FOREIGN KEY referencing `analytics`._id)
    *   `amount` (INT, NOT NULL)
    *   `date` (DATE, NOT NULL)
*   **Clave Primaria:** `_id`
*   **Clave Foránea:** `analytics_id`
*   **Restricciones:** UNIQUE(`analytics_id`, `date`)

### Tabla: `posts`

*   **Nombre:** `posts`
*   **Columnas:**
    *   `_id` (VARCHAR(255), NOT NULL, PRIMARY KEY)
    *   `author_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
    *   `static_url` (VARCHAR(255), NULL)
    *   `caption` (TEXT, NULL)
    *   `category` (VARCHAR(255), NULL)
    *   `createdAt` (DATETIME, NOT NULL)
    *   `lastEditedAt` (DATETIME, NOT NULL)
*   **Clave Primaria:** `_id`
*   **Clave Foránea:** `author_id`

### Tabla: `post_comments`

*   **Nombre:** `post_comments`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `post_id` (VARCHAR(255), NOT NULL, FOREIGN KEY referencing `posts`._id)
    *   `by_username` (VARCHAR(255), NOT NULL)
    *   `text` (TEXT, NOT NULL)
*   **Clave Primaria:** `_id`
*   **Clave Foránea:** `post_id`

### Tabla: `post_likes`

*   **Nombre:** `post_likes`
*   **Columnas:**
    *   `post_id` (VARCHAR(255), NOT NULL, FOREIGN KEY referencing `posts`._id)
    *   `user_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
*   **Clave Primaria:** (`post_id`, `user_id`)
*   **Clave Foránea:** `post_id`, `user_id`

### Tabla: `rooms`

*   **Nombre:** `rooms`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `id` (VARCHAR(255), NOT NULL, UNIQUE)
*   **Clave Primaria:** `_id`

### Tabla: `room_users`

*   **Nombre:** `room_users`
*   **Columnas:**
    *   `room_id` (INT, NOT NULL, FOREIGN KEY referencing `rooms`._id)
    *   `user_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
*   **Clave Primaria:** (`room_id`, `user_id`)
*   **Clave Foránea:** `room_id`, `user_id`

### Tabla: `chats`

*   **Nombre:** `chats`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `room_id` (INT, NOT NULL, FOREIGN KEY referencing `rooms`._id)
    *   `txt` (TEXT, NOT NULL)
    *   `time` (DATETIME, NOT NULL)
    *   `by_user_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
*   **Clave Primaria:** `_id`
*   **Clave Foránea:** `room_id`, `by_user_id`

### Tabla: `keys`

*   **Nombre:** `keys`
*   **Columnas:**
    *   `apiKey` (VARCHAR(255), NOT NULL, PRIMARY KEY, UNIQUE)
    *   `invokes` (INT, NOT NULL)
*   **Clave Primaria:** `apiKey`

### Tabla: `key_stats`

*   **Nombre:** `key_stats`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `key_apiKey` (VARCHAR(255), NOT NULL, FOREIGN KEY referencing `keys`._apiKey)
    *   `time` (DATETIME, NOT NULL)
    *   `request` (TEXT, NULL)
*   **Clave Primaria:** `_id`
*   **Clave Foránea:** `key_apiKey`

### Tabla: `user_followers`

*   **Nombre:** `user_followers`
*   **Columnas:**
    *   `user_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
    *   `follower_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
*   **Clave Primaria:** (`user_id`, `follower_id`)
*   **Clave Foránea:** `user_id`, `follower_id`

### Tabla: `user_notifications`

*   **Nombre:** `user_notifications`
*   **Columnas:**
    *   `_id` (INT, NOT NULL, PRIMARY KEY)
    *   `user_id` (INT, NOT NULL, FOREIGN KEY referencing `users`._id)
    *   `msg` (TEXT, NULL)
    *   `link` (VARCHAR(255), NULL)
    *   `time` (DATETIME, NULL)
*   **Clave Primaria:** `_id`
*   **Clave Foránea:** `user_id`
