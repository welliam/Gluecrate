drop table if exists pastes;

create table pastes (
    id integer primary key,
    title text not null,
    author text not null,
    inserted_at integer not null,
    edited_from integer
);

/* i did
 * alter table pastes add column edited_from integer
 */
