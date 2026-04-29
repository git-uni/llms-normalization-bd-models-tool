```sql
CREATE TABLE users (
    _id NUMBER NOT NULL,
    username VARCHAR2(255) NOT NULL,
    firstname VARCHAR2(255),
    lastname VARCHAR2(255),
    dob VARCHAR2(255),
    bio CLOB,
    profile_pic VARCHAR2(255),
    password VARCHAR2(255) NOT NULL,
    lastLogin TIMESTAMP,
    developer BOOLEAN,
    CONSTRAINT users_pk PRIMARY KEY (_id),
    CONSTRAINT users_username_uk UNIQUE (username)
);

CREATE TABLE analytics (
    _id NUMBER NOT NULL,
    name VARCHAR2(255) NOT NULL,
    CONSTRAINT analytics_pk PRIMARY KEY (_id),
    CONSTRAINT analytics_name_uk UNIQUE (name)
);

CREATE TABLE analytics_stats (
    _id NUMBER NOT NULL,
    analytics_id NUMBER NOT NULL,
    amount NUMBER NOT NULL,
    date DATE NOT NULL,
    CONSTRAINT analytics_stats_pk PRIMARY KEY (_id),
    CONSTRAINT analytics_stats_fk FOREIGN KEY (analytics_id) REFERENCES analytics(_id),
    CONSTRAINT analytics_stats_uk UNIQUE (analytics_id, date)
);

CREATE TABLE keys (
    apiKey VARCHAR2(255) NOT NULL,
    invokes NUMBER NOT NULL,
    CONSTRAINT keys_pk PRIMARY KEY (apiKey),
    CONSTRAINT keys_apiKey_uk UNIQUE (apiKey)
);

CREATE TABLE key_stats (
    _id NUMBER NOT NULL,
    key_apiKey VARCHAR2(255) NOT NULL,
    time TIMESTAMP NOT NULL,
    request CLOB,
    CONSTRAINT key_stats_pk PRIMARY KEY (_id),
    CONSTRAINT key_stats_fk FOREIGN KEY (key_apiKey) REFERENCES keys(apiKey)
);

CREATE TABLE rooms (
    _id NUMBER NOT NULL,
    id VARCHAR2(255) NOT NULL,
    CONSTRAINT rooms_pk PRIMARY KEY (_id),
    CONSTRAINT rooms_id_uk UNIQUE (id)
);

CREATE TABLE posts (
    _id VARCHAR2(255) NOT NULL,
    author_id NUMBER NOT NULL,
    static_url VARCHAR2(255),
    caption CLOB,
    category VARCHAR2(255),
    createdAt TIMESTAMP NOT NULL,
    lastEditedAt TIMESTAMP NOT NULL,
    CONSTRAINT posts_pk PRIMARY KEY (_id),
    CONSTRAINT posts_fk FOREIGN KEY (author_id) REFERENCES users(_id)
);

CREATE TABLE post_comments (
    _id NUMBER NOT NULL,
    post_id VARCHAR2(255) NOT NULL,
    by_username VARCHAR2(255) NOT NULL,
    text CLOB NOT NULL,
    CONSTRAINT post_comments_pk PRIMARY KEY (_id),
    CONSTRAINT post_comments_fk FOREIGN KEY (post_id) REFERENCES posts(_id)
);

CREATE TABLE post_likes (
    post_id VARCHAR2(255) NOT NULL,
    user_id NUMBER NOT NULL,
    CONSTRAINT post_likes_pk PRIMARY KEY (post_id, user_id),
    CONSTRAINT post_likes_fk1 FOREIGN KEY (post_id) REFERENCES posts(_id),
    CONSTRAINT post_likes_fk2 FOREIGN KEY (user_id) REFERENCES users(_id)
);

CREATE TABLE room_users (
    room_id NUMBER NOT NULL,
    user_id NUMBER NOT NULL,
    CONSTRAINT room_users_pk PRIMARY KEY (room_id, user_id),
    CONSTRAINT room_users_fk1 FOREIGN KEY (room_id) REFERENCES rooms(_id),
    CONSTRAINT room_users_fk2 FOREIGN KEY (user_id) REFERENCES users(_id)
);

CREATE TABLE chats (
    _id NUMBER NOT NULL,
    room_id NUMBER NOT NULL,
    txt CLOB NOT NULL,
    time TIMESTAMP NOT NULL,
    by_user_id NUMBER NOT NULL,
    CONSTRAINT chats_pk PRIMARY KEY (_id),
    CONSTRAINT chats_fk1 FOREIGN KEY (room_id) REFERENCES rooms(_id),
    CONSTRAINT chats_fk2 FOREIGN KEY (by_user_id) REFERENCES users(_id)
);

CREATE TABLE user_followers (
    user_id NUMBER NOT NULL,
    follower_id NUMBER NOT NULL,
    CONSTRAINT user_followers_pk PRIMARY KEY (user_id, follower_id),
    CONSTRAINT user_followers_fk1 FOREIGN KEY (user_id) REFERENCES users(_id),
    CONSTRAINT user_followers_fk2 FOREIGN KEY (follower_id) REFERENCES users(_id)
);

CREATE TABLE user_notifications (
    _id NUMBER NOT NULL,
    user_id NUMBER NOT NULL,
    msg CLOB,
    link VARCHAR2(255),
    time TIMESTAMP,
    CONSTRAINT user_notifications_pk PRIMARY KEY (_id),
    CONSTRAINT user_notifications_fk FOREIGN KEY (user_id) REFERENCES users(_id)
);
```