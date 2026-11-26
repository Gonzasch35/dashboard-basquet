-- =====================================================================
-- TP Final Parte 2 - Base de Datos
-- Liga de Basquet Formativo de Parana (U13, U15, U17 y U19) - PostgreSQL
-- 01_ddl_liga_basquet.sql: crea las 14 tablas con todas sus reglas
-- Integrantes: Tomiozzo Franco y Schmidt Gonzalo
-- =====================================================================
-- Resumen de la liga (el detalle esta en Planificacion_TP_Final_Parte_2):
--  * 12 clubes, cada uno con 4 equipos (uno por categoria) y su cancha.
--  * Por temporada: Apertura (la ida, 11 fechas) y Clausura (la vuelta).
--    Cada categoria juega su propio torneo.
--  * Playoff por categoria: cuartos y semis al mejor de 3, final a un
--    partido en cancha neutral.
--  * 16 jugadores por equipo y por torneo, dorsal del 4 al 19.
--  * 2 arbitros por partido (+ suplente si falta alguno).
--  * W.O.: el que no se presenta pierde 20 a 0.
-- Nada tiene el anio escrito: la temporada sale siempre de la tabla torneo.
-- =====================================================================

-- borro todo en orden inverso al que se crea (primero las que tienen FK),
-- asi el archivo se puede correr las veces que haga falta
drop table if exists estadistica;
drop table if exists arbitro_partido;
drop table if exists partido;
drop table if exists serie;
drop table if exists pase;
drop table if exists plantel;
drop table if exists torneo;
drop table if exists equipo;
drop table if exists cancha;
drop table if exists entrenador;
drop table if exists arbitro;
drop table if exists jugador;
drop table if exists categoria;
drop table if exists club;


-- =====================================================================
-- 1) TABLAS QUE NO DEPENDEN DE NADIE
-- =====================================================================

create table club (
    id_club serial,
    nombre varchar(50) not null,
    ciudad varchar(40) not null,
    direccion varchar(80),
    telefono varchar(20),
    constraint pk_club primary key (id_club),
    constraint uq_club_nombre unique (nombre)
);

-- la edad se calcula como (temporada - anio de nacimiento).
-- ej. en 2026 la U13 son los nacidos en 2014 y 2015 -> edades 11 y 12
-- nivel_eneba_minimo: lo que tiene que tener el entrenador para dirigirla
-- (U13 = 1, U15 = 2, U17 = 2, U19 = 3)
create table categoria (
    id_categoria serial,
    nombre varchar(10) not null,
    edad_minima int not null,
    edad_maxima int not null,
    nivel_eneba_minimo int not null,
    constraint pk_categoria primary key (id_categoria),
    constraint uq_categoria_nombre unique (nombre),
    constraint ck_categoria_edades check (edad_minima between 8 and 21
                                          and edad_maxima between 8 and 21
                                          and edad_minima <= edad_maxima),
    constraint ck_categoria_nivel check (nivel_eneba_minimo between 1 and 3)
);

create table jugador (
    dni_jugador int,
    nombre varchar(40) not null,
    apellido varchar(40) not null,
    fecha_nacimiento date not null,
    posicion varchar(15),
    altura_cm int,
    constraint pk_jugador primary key (dni_jugador),
    constraint ck_jugador_posicion check (posicion in ('Base', 'Escolta', 'Alero', 'Ala-pivot', 'Pivot')),
    constraint ck_jugador_altura check (altura_cm between 120 and 230)
);

create table arbitro (
    dni_arbitro int,
    nombre varchar(40) not null,
    apellido varchar(40) not null,
    categoria_arbitro varchar(20) not null,
    constraint pk_arbitro primary key (dni_arbitro),
    constraint ck_arbitro_categoria check (categoria_arbitro in ('Nacional', 'Provincial', 'Aspirante'))
);


-- =====================================================================
-- 2) TABLAS QUE DEPENDEN DE CLUB
-- =====================================================================

-- cada entrenador trabaja en UN solo club (puede dirigir varias categorias de ese club)
create table entrenador (
    dni_entrenador int,
    nombre varchar(40) not null,
    apellido varchar(40) not null,
    telefono varchar(20),
    nivel_eneba int not null,
    id_club int not null,
    constraint pk_entrenador primary key (dni_entrenador),
    constraint fk_entrenador_club foreign key (id_club) references club(id_club),
    -- este unique lo necesita la FK compuesta de equipo (dni_entrenador, id_club)
    constraint uq_entrenador_club unique (dni_entrenador, id_club),
    constraint ck_entrenador_nivel check (nivel_eneba between 1 and 3)
);

-- una cancha por club. La capacidad sirve para elegir la cancha neutral de la final
create table cancha (
    id_cancha serial,
    nombre varchar(60) not null,
    direccion varchar(80),
    capacidad int not null,
    id_club int not null,
    constraint pk_cancha primary key (id_cancha),
    constraint fk_cancha_club foreign key (id_club) references club(id_club),
    constraint uq_cancha_nombre unique (nombre),
    constraint uq_cancha_club unique (id_club),          -- un club, una cancha
    constraint ck_cancha_capacidad check (capacidad > 0)
);


-- =====================================================================
-- 3) EQUIPOS Y TORNEOS
-- =====================================================================

-- el entrenador del equipo tiene que ser del MISMO club: por eso la FK
-- es compuesta (dni_entrenador, id_club) contra entrenador
create table equipo (
    id_equipo serial,
    nombre varchar(60) not null,
    id_club int not null,
    id_categoria int not null,
    dni_entrenador int not null,
    constraint pk_equipo primary key (id_equipo),
    constraint fk_equipo_club foreign key (id_club) references club(id_club),
    constraint fk_equipo_categoria foreign key (id_categoria) references categoria(id_categoria),
    constraint fk_equipo_entrenador foreign key (dni_entrenador, id_club)
        references entrenador(dni_entrenador, id_club),
    constraint uq_equipo_club_categoria unique (id_club, id_categoria),  -- un equipo por categoria en cada club
    -- lo usan las FK compuestas de plantel, pase y partido (equipo + categoria)
    constraint uq_equipo_categoria unique (id_equipo, id_categoria)
);

-- Apertura y Clausura de cada temporada, uno por categoria
create table torneo (
    id_torneo serial,
    nombre varchar(20) not null,
    temporada int not null,
    id_categoria int not null,
    fecha_inicio date not null,
    fecha_fin date,
    constraint pk_torneo primary key (id_torneo),
    constraint fk_torneo_categoria foreign key (id_categoria) references categoria(id_categoria),
    constraint uq_torneo unique (nombre, temporada, id_categoria),
    -- lo usan las FK compuestas de plantel y partido (torneo + categoria)
    constraint uq_torneo_categoria unique (id_torneo, id_categoria),
    constraint ck_torneo_nombre check (nombre in ('Apertura', 'Clausura')),
    constraint ck_torneo_fechas check (fecha_fin >= fecha_inicio)
);


-- =====================================================================
-- 4) JUGADORES EN LOS EQUIPOS
-- =====================================================================

-- relacion N:M entre jugador y equipo, POR TORNEO: asi un jugador puede
-- estar en un club en el Apertura y en otro en el Clausura (pase)
-- id_categoria: el equipo y el torneo tienen que ser de la MISMA categoria.
-- Como las dos FK compuestas usan la misma columna, no se puede cargar un
-- equipo U15 en un torneo U17 (antes lo revisaba el control C3)
create table plantel (
    id_equipo int,
    dni_jugador int,
    id_torneo int,
    id_categoria int not null,
    numero_camiseta int not null,
    constraint pk_plantel primary key (id_equipo, dni_jugador, id_torneo),
    constraint fk_plantel_equipo foreign key (id_equipo, id_categoria) references equipo(id_equipo, id_categoria),
    constraint fk_plantel_jugador foreign key (dni_jugador) references jugador(dni_jugador),
    constraint fk_plantel_torneo foreign key (id_torneo, id_categoria) references torneo(id_torneo, id_categoria),
    constraint uq_plantel_jugador unique (dni_jugador, id_torneo),   -- en un torneo, un solo equipo
    constraint uq_plantel_camiseta unique (id_equipo, id_torneo, numero_camiseta),
    constraint ck_plantel_camiseta check (numero_camiseta between 4 and 19)
);

-- registro de los pases (se hacen entre el Apertura y el Clausura).
-- son intercambios: si un equipo recibe uno, entrega otro y siguen con 16
-- id_categoria: origen y destino son de la misma categoria, con la misma
-- tecnica de FK compuesta (antes lo revisaba el control C6)
create table pase (
    id_pase serial,
    dni_jugador int not null,
    id_equipo_origen int not null,
    id_equipo_destino int not null,
    id_categoria int not null,
    temporada int not null,
    fecha_pase date not null,
    constraint pk_pase primary key (id_pase),
    constraint fk_pase_jugador foreign key (dni_jugador) references jugador(dni_jugador),
    constraint fk_pase_origen foreign key (id_equipo_origen, id_categoria) references equipo(id_equipo, id_categoria),
    constraint fk_pase_destino foreign key (id_equipo_destino, id_categoria) references equipo(id_equipo, id_categoria),
    constraint uq_pase unique (dni_jugador, temporada),               -- un pase por temporada
    constraint ck_pase_equipos check (id_equipo_origen <> id_equipo_destino)
);


-- =====================================================================
-- 5) PARTIDOS
-- =====================================================================

-- series de playoff (cuartos y semis al mejor de 3). La final es un solo partido, sin serie
create table serie (
    id_serie serial,
    id_torneo int not null,
    fase varchar(15) not null,
    id_equipo_mejor int not null,      -- el mejor ubicado: es local en el partido 1 y en el 3
    id_equipo_peor int not null,
    id_equipo_ganador int,             -- queda vacio hasta que se define
    constraint pk_serie primary key (id_serie),
    constraint fk_serie_torneo foreign key (id_torneo) references torneo(id_torneo),
    constraint fk_serie_mejor foreign key (id_equipo_mejor) references equipo(id_equipo),
    constraint fk_serie_peor foreign key (id_equipo_peor) references equipo(id_equipo),
    constraint fk_serie_ganador foreign key (id_equipo_ganador) references equipo(id_equipo),
    constraint uq_serie_torneo unique (id_serie, id_torneo),     -- lo usa la FK compuesta de partido
    constraint ck_serie_fase check (fase in ('Cuartos', 'Semifinal')),
    constraint ck_serie_equipos check (id_equipo_mejor <> id_equipo_peor),
    constraint ck_serie_ganador check (id_equipo_ganador is null
                                       or id_equipo_ganador in (id_equipo_mejor, id_equipo_peor))
);

-- id_categoria: local, visitante y torneo de la misma categoria
-- (antes lo revisaba el control C9)
create table partido (
    id_partido serial,
    id_torneo int not null,
    id_categoria int not null,
    fase varchar(15) not null,
    nro_fecha int,                    -- solo fase regular (1 a 11)
    id_serie int,                     -- solo cuartos y semis
    nro_partido_serie int,            -- 1, 2 o 3
    fecha date not null,              -- el dia en que se jugo de verdad
    hora time not null,
    id_cancha int not null,
    id_equipo_local int not null,
    id_equipo_visitante int not null,
    puntos_local int,
    puntos_visitante int,
    id_equipo_ausente int,            -- W.O.: el equipo que no se presento
    fecha_original date,              -- si se postergo: cuando se iba a jugar
    hora_original time,
    motivo_postergacion varchar(100),
    constraint pk_partido primary key (id_partido),
    constraint fk_partido_torneo foreign key (id_torneo, id_categoria) references torneo(id_torneo, id_categoria),
    -- la serie tiene que ser del mismo torneo que el partido
    constraint fk_partido_serie foreign key (id_serie, id_torneo) references serie(id_serie, id_torneo),
    constraint fk_partido_cancha foreign key (id_cancha) references cancha(id_cancha),
    constraint fk_partido_local foreign key (id_equipo_local, id_categoria) references equipo(id_equipo, id_categoria),
    constraint fk_partido_visitante foreign key (id_equipo_visitante, id_categoria) references equipo(id_equipo, id_categoria),
    constraint fk_partido_ausente foreign key (id_equipo_ausente) references equipo(id_equipo),
    constraint uq_partido_torneo unique (id_partido, id_torneo),        -- lo usa la FK compuesta de estadistica
    constraint uq_partido_cancha_horario unique (id_cancha, fecha, hora), -- una cancha, un partido a la vez
    constraint uq_partido_serie unique (id_serie, nro_partido_serie),
    constraint ck_partido_equipos check (id_equipo_local <> id_equipo_visitante),
    constraint ck_partido_puntos check (puntos_local >= 0 and puntos_visitante >= 0),
    constraint ck_partido_sin_empate check (puntos_local <> puntos_visitante),  -- en basquet no hay empate
    constraint ck_partido_fase check (fase in ('Regular', 'Cuartos', 'Semifinal', 'Final')),
    -- cada fase con lo suyo: la regular lleva nro_fecha; cuartos y semis llevan serie
    constraint ck_partido_fase_datos check (
        (fase = 'Regular' and nro_fecha between 1 and 11 and id_serie is null and nro_partido_serie is null)
     or (fase in ('Cuartos', 'Semifinal') and nro_fecha is null and id_serie is not null
         and nro_partido_serie between 1 and 3)
     or (fase = 'Final' and nro_fecha is null and id_serie is null and nro_partido_serie is null)
    ),
    -- dias y horarios (extract(dow): 0 = domingo, 1 = lunes ... 5 = viernes, 6 = sabado)
    --  * si NO se postergo: se juega viernes, sabado o domingo. En la fase regular:
    --    viernes 19:00 o 21:30; sabado y domingo 11:00, 14:00, 17:00 o 20:00
    --  * si se postergo: de lunes a jueves, a las 18:00 o a las 20:00 (despues de la escuela)
    constraint ck_partido_dia_horario check (
        (fecha_original is null and fase = 'Regular'
            and ((extract(dow from fecha) = 5 and hora in ('19:00', '21:30'))
              or (extract(dow from fecha) in (6, 0) and hora in ('11:00', '14:00', '17:00', '20:00'))))
     or (fecha_original is null and fase <> 'Regular' and extract(dow from fecha) in (5, 6, 0))
     or (fecha_original is not null and extract(dow from fecha) between 1 and 4
            and hora in ('18:00', '20:00'))
    ),
    -- si se postergo, tiene que estar la fecha y hora original y el motivo (y al reves)
    constraint ck_partido_postergado check (
        (fecha_original is null and hora_original is null and motivo_postergacion is null)
     or (fecha_original is not null and hora_original is not null and motivo_postergacion is not null
         and fecha_original < fecha)
    ),
    -- W.O.: solo en fase regular, el ausente es uno de los dos y el resultado es 20 a 0
    constraint ck_partido_wo check (
        id_equipo_ausente is null
     or (fase = 'Regular' and id_equipo_ausente = id_equipo_local and puntos_local = 0 and puntos_visitante = 20)
     or (fase = 'Regular' and id_equipo_ausente = id_equipo_visitante and puntos_local = 20 and puntos_visitante = 0)
    )
);

-- una sola final por torneo: indice unico PARCIAL (solo mira las filas con fase = 'Final')
create unique index uq_partido_final on partido (id_torneo) where fase = 'Final';

-- arbitros de cada partido: un principal, un auxiliar y, si falta uno, un suplente
create table arbitro_partido (
    id_partido int,
    dni_arbitro int,
    rol varchar(15) not null,
    asistencia varchar(15) not null default 'Presente',
    observacion varchar(100),
    dni_reemplazado int,              -- solo el suplente: a quien reemplazo
    constraint pk_arbitro_partido primary key (id_partido, dni_arbitro),
    constraint fk_ap_partido foreign key (id_partido) references partido(id_partido),
    constraint fk_ap_arbitro foreign key (dni_arbitro) references arbitro(dni_arbitro),
    constraint fk_ap_reemplazado foreign key (dni_reemplazado) references arbitro(dni_arbitro),
    constraint uq_ap_rol unique (id_partido, rol),     -- un principal, un auxiliar y como mucho un suplente
    constraint ck_ap_rol check (rol in ('Principal', 'Auxiliar', 'Suplente')),
    constraint ck_ap_asistencia check (asistencia in ('Presente', 'Llegó tarde', 'Ausente')),
    -- el suplente dice a quien reemplaza; los otros no
    constraint ck_ap_suplente check ((rol = 'Suplente' and dni_reemplazado is not null and dni_reemplazado <> dni_arbitro)
                                     or (rol <> 'Suplente' and dni_reemplazado is null)),
    -- si faltó o llegó tarde, se anota por qué
    constraint ck_ap_observacion check (asistencia = 'Presente' or observacion is not null)
);

-- la planilla de cada jugador en cada partido
--  * fk_est_plantel: el jugador tiene que estar en el plantel de ESE equipo en ESE torneo
--  * fk_est_partido: el torneo tiene que ser el mismo del partido
create table estadistica (
    id_partido int,
    dni_jugador int,
    id_equipo int not null,
    id_torneo int not null,
    minutos int not null default 0,
    libres int not null default 0,      -- tiros libres convertidos (1 punto)
    dobles int not null default 0,      -- dobles convertidos (2 puntos)
    triples int not null default 0,     -- triples convertidos (3 puntos)
    puntos int not null default 0,
    rebotes int not null default 0,
    asistencias int not null default 0,
    faltas int not null default 0,
    constraint pk_estadistica primary key (id_partido, dni_jugador),
    constraint fk_est_partido foreign key (id_partido, id_torneo) references partido(id_partido, id_torneo),
    constraint fk_est_plantel foreign key (id_equipo, dni_jugador, id_torneo)
        references plantel(id_equipo, dni_jugador, id_torneo),
    constraint ck_est_minutos check (minutos between 0 and 50),     -- 40 + suplementarios
    constraint ck_est_valores check (libres >= 0 and dobles >= 0 and triples >= 0
                                     and rebotes >= 0 and asistencias >= 0),
    constraint ck_est_puntos check (puntos = libres + 2 * dobles + 3 * triples),
    constraint ck_est_faltas check (faltas between 0 and 5)
);
