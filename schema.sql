drop table if exists pastes;

create table pastes (
    id integer primary key,
    title text not null,
    author text not null,
    inserted_at integer not null
);
