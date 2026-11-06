-- =====================================================================
-- TP Final Parte 2 - Base de Datos
-- 03_controles.sql: revisa las reglas que el DDL no puede frenar solo
-- Integrantes: Tomiozzo Franco y Schmidt Gonzalo
-- Correr DESPUES de 01 y 02.
-- =====================================================================
-- Como se leen: cada control BUSCA LAS FILAS QUE ROMPEN la regla.
-- Si devuelve 0 filas, la regla se cumple. (El ultimo, el de W.O., es
-- solo informativo y si devuelve filas.)
-- Al final hay 4 consultas de ejemplo para ver que la base tiene sentido.
-- =====================================================================


-- ---------------------------------------------------------------------
-- ENTRENADORES Y EQUIPOS
-- ---------------------------------------------------------------------

-- C1) el nivel ENEBA del entrenador alcanza para la categoria que dirige
--     (nivel 1: solo U13; nivel 2: hasta U17; nivel 3: todas)
select eq.nombre as equipo, en.apellido as entrenador, en.nivel_eneba, ca.nombre as categoria,
       ca.nivel_eneba_minimo
from equipo eq, entrenador en, categoria ca
where eq.dni_entrenador = en.dni_entrenador
  and eq.id_categoria = ca.id_categoria
  and en.nivel_eneba < ca.nivel_eneba_minimo;

-- C2) cada equipo tiene exactamente 16 jugadores en cada torneo de su categoria
select eq.nombre as equipo, t.nombre as torneo, count(pl.dni_jugador) as jugadores
from equipo eq
join torneo t on t.id_categoria = eq.id_categoria
left join plantel pl on pl.id_equipo = eq.id_equipo and pl.id_torneo = t.id_torneo
group by eq.nombre, t.nombre
having count(pl.dni_jugador) <> 16;

-- C3) el plantel es de la categoria del torneo (un equipo U15 no puede estar en un torneo U17)
select pl.id_equipo, pl.dni_jugador, pl.id_torneo
from plantel pl, equipo eq, torneo t
where pl.id_equipo = eq.id_equipo
  and pl.id_torneo = t.id_torneo
  and eq.id_categoria <> t.id_categoria;

-- C4) la edad del jugador (temporada - anio de nacimiento) corresponde a su categoria
select j.apellido, j.nombre, j.fecha_nacimiento, t.temporada, ca.nombre as categoria
from jugador j, plantel pl, torneo t, categoria ca
where j.dni_jugador = pl.dni_jugador
  and pl.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
  and (t.temporada - extract(year from j.fecha_nacimiento)) not between ca.edad_minima and ca.edad_maxima;


-- ---------------------------------------------------------------------
-- PASES Y DORSALES
-- ---------------------------------------------------------------------

-- C5) los pases son intercambios: si un jugador va de A a B, otro tiene que ir de B a A
select pa.dni_jugador, pa.id_equipo_origen, pa.id_equipo_destino
from pase pa
where not exists (select 1
                  from pase pb
                  where pb.temporada = pa.temporada
                    and pb.id_equipo_origen = pa.id_equipo_destino
                    and pb.id_equipo_destino = pa.id_equipo_origen);

-- C6) los pases son entre equipos de la misma categoria
select pa.dni_jugador
from pase pa, equipo eo, equipo ed
where pa.id_equipo_origen = eo.id_equipo
  and pa.id_equipo_destino = ed.id_equipo
  and eo.id_categoria <> ed.id_categoria;

-- C7) el pase coincide con los planteles: en el Apertura estaba en el origen
--     y en el Clausura esta en el destino
select pa.dni_jugador
from pase pa
where not exists (select 1 from plantel pl, torneo t
                  where pl.id_torneo = t.id_torneo and t.nombre = 'Apertura' and t.temporada = pa.temporada
                    and pl.dni_jugador = pa.dni_jugador and pl.id_equipo = pa.id_equipo_origen)
   or not exists (select 1 from plantel pl, torneo t
                  where pl.id_torneo = t.id_torneo and t.nombre = 'Clausura' and t.temporada = pa.temporada
                    and pl.dni_jugador = pa.dni_jugador and pl.id_equipo = pa.id_equipo_destino);

-- C8) el que sigue en el mismo equipo del Apertura al Clausura mantiene el dorsal
select pa.dni_jugador, pa.numero_camiseta as dorsal_apertura, pc.numero_camiseta as dorsal_clausura
from plantel pa, plantel pc, torneo ta, torneo tc
where pa.dni_jugador = pc.dni_jugador
  and pa.id_equipo = pc.id_equipo
  and pa.id_torneo = ta.id_torneo and ta.nombre = 'Apertura'
  and pc.id_torneo = tc.id_torneo and tc.nombre = 'Clausura'
  and ta.temporada = tc.temporada
  and pa.numero_camiseta <> pc.numero_camiseta;


-- ---------------------------------------------------------------------
-- PARTIDOS Y CALENDARIO
-- ---------------------------------------------------------------------

-- C9) los dos equipos del partido son de la categoria del torneo
select p.id_partido
from partido p, torneo t, equipo l, equipo v
where p.id_torneo = t.id_torneo
  and p.id_equipo_local = l.id_equipo
  and p.id_equipo_visitante = v.id_equipo
  and (l.id_categoria <> t.id_categoria or v.id_categoria <> t.id_categoria);

-- C10) en fase regular cada equipo juega 11 partidos por torneo (uno contra cada rival)
select t.id_torneo, eq.nombre as equipo, count(*) as partidos
from partido p, torneo t, equipo eq
where p.id_torneo = t.id_torneo
  and p.fase = 'Regular'
  and eq.id_equipo in (p.id_equipo_local, p.id_equipo_visitante)
group by t.id_torneo, eq.nombre
having count(*) <> 11;

-- C11) salvo la final, se juega en la cancha del club local
select p.id_partido, p.fase
from partido p, equipo l, cancha c
where p.id_equipo_local = l.id_equipo
  and p.id_cancha = c.id_cancha
  and p.fase <> 'Final'
  and c.id_club <> l.id_club;

-- C12) U13 y U15 no juegan los viernes (en ninguna fase)
select p.id_partido, p.fecha, ca.nombre as categoria
from partido p, torneo t, categoria ca
where p.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
  and extract(dow from p.fecha) = 5
  and ca.nombre in ('U13', 'U15');

-- C13) los postergados respetan el horario de su categoria (18:00 U13/U15, 20:00 U17/U19)
select p.id_partido, ca.nombre as categoria, p.hora
from partido p, torneo t, categoria ca
where p.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
  and p.fecha_original is not null
  and ((ca.nombre in ('U13', 'U15') and p.hora <> '18:00')
    or (ca.nombre in ('U17', 'U19') and p.hora <> '20:00'));

-- C14) todo partido que no fue W.O. tiene planilla (estadisticas)
select p.id_partido
from partido p
where p.id_equipo_ausente is null
  and not exists (select 1 from estadistica e where e.id_partido = p.id_partido);

-- C15) los partidos con W.O. NO tienen estadisticas
select p.id_partido
from partido p
where p.id_equipo_ausente is not null
  and exists (select 1 from estadistica e where e.id_partido = p.id_partido);


-- ---------------------------------------------------------------------
-- PLAYOFF
-- ---------------------------------------------------------------------

-- C16) en las series el mejor ubicado es local en el 1 y en el 3, y el peor en el 2
select p.id_partido, s.id_serie, p.nro_partido_serie
from partido p, serie s
where p.id_serie = s.id_serie
  and ((p.nro_partido_serie in (1, 3) and p.id_equipo_local <> s.id_equipo_mejor)
    or (p.nro_partido_serie = 2 and p.id_equipo_local <> s.id_equipo_peor));

-- C17) el 3er partido solo existe si iban 1 a 1
--      (si el mismo equipo gano el 1 y el 2, no tendria que haber 3ro)
select s.id_serie
from serie s
where exists (select 1 from partido p3 where p3.id_serie = s.id_serie and p3.nro_partido_serie = 3)
  and 1 = (select count(distinct case when p.puntos_local > p.puntos_visitante
                                      then p.id_equipo_local else p.id_equipo_visitante end)
           from partido p
           where p.id_serie = s.id_serie and p.nro_partido_serie in (1, 2));

-- C18) el ganador cargado en la serie es el que gano 2 partidos
select s.id_serie
from serie s
where s.id_equipo_ganador not in (select case when p.puntos_local > p.puntos_visitante
                                              then p.id_equipo_local else p.id_equipo_visitante end
                                  from partido p
                                  where p.id_serie = s.id_serie
                                  group by 1
                                  having count(*) = 2);

-- C19) la final se juega en la cancha de mayor capacidad entre los clubes que NO juegan la final
select p.id_partido, c.nombre as cancha
from partido p, cancha c
where p.fase = 'Final'
  and p.id_cancha = c.id_cancha
  and (c.id_club in (select eq.id_club from equipo eq
                     where eq.id_equipo in (p.id_equipo_local, p.id_equipo_visitante))
    or c.capacidad < (select max(c2.capacidad)
                      from cancha c2
                      where c2.id_club not in (select eq.id_club from equipo eq
                                               where eq.id_equipo in (p.id_equipo_local, p.id_equipo_visitante))));


-- ---------------------------------------------------------------------
-- ARBITROS
-- ---------------------------------------------------------------------

-- C20) ningun arbitro dirige mas de 2 partidos en un dia (el que falto no cuenta)
select ap.dni_arbitro, p.fecha, count(*) as partidos
from arbitro_partido ap, partido p
where ap.id_partido = p.id_partido
  and ap.asistencia <> 'Ausente'
group by ap.dni_arbitro, p.fecha
having count(*) > 2;

-- C21) ningun arbitro esta en 2 partidos a la misma hora
select ap.dni_arbitro, p.fecha, p.hora
from arbitro_partido ap, partido p
where ap.id_partido = p.id_partido
  and ap.asistencia <> 'Ausente'
group by ap.dni_arbitro, p.fecha, p.hora
having count(*) > 1;

-- C22) los aspirantes dirigen solo U13 y U15
select ap.id_partido, a.apellido, ca.nombre as categoria
from arbitro_partido ap, arbitro a, partido p, torneo t, categoria ca
where ap.dni_arbitro = a.dni_arbitro
  and ap.id_partido = p.id_partido
  and p.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
  and a.categoria_arbitro = 'Aspirante'
  and ca.nombre not in ('U13', 'U15');

-- C23) cada final tiene al menos un arbitro Nacional que estuvo
select p.id_partido
from partido p
where p.fase = 'Final'
  and not exists (select 1 from arbitro_partido ap, arbitro a
                  where ap.id_partido = p.id_partido
                    and ap.dni_arbitro = a.dni_arbitro
                    and a.categoria_arbitro = 'Nacional'
                    and ap.asistencia <> 'Ausente');

-- C24) cada partido tiene principal y auxiliar
select p.id_partido
from partido p
where 2 <> (select count(*) from arbitro_partido ap
            where ap.id_partido = p.id_partido and ap.rol in ('Principal', 'Auxiliar'));

-- C25) si un arbitro falto, ese partido tiene suplente que lo reemplazo
select ap.id_partido, ap.dni_arbitro
from arbitro_partido ap
where ap.asistencia = 'Ausente'
  and not exists (select 1 from arbitro_partido s
                  where s.id_partido = ap.id_partido
                    and s.rol = 'Suplente'
                    and s.dni_reemplazado = ap.dni_arbitro);

-- C26) en los W.O. hubo al menos un arbitro presente para dejar constancia
select p.id_partido
from partido p
where p.id_equipo_ausente is not null
  and not exists (select 1 from arbitro_partido ap
                  where ap.id_partido = p.id_partido and ap.asistencia <> 'Ausente');


-- ---------------------------------------------------------------------
-- ESTADISTICAS
-- ---------------------------------------------------------------------

-- C27) el equipo de cada estadistica es el local o el visitante de ese partido
select e.id_partido, e.dni_jugador, e.id_equipo
from estadistica e, partido p
where e.id_partido = p.id_partido
  and e.id_equipo <> p.id_equipo_local
  and e.id_equipo <> p.id_equipo_visitante;

-- C28) como mucho 12 jugadores por equipo en cada partido
select e.id_partido, e.id_equipo, count(*) as jugadores
from estadistica e
group by e.id_partido, e.id_equipo
having count(*) > 12;

-- C29) la suma de los puntos de los jugadores da el resultado del partido
select p.id_partido, p.puntos_local, p.puntos_visitante
from partido p, estadistica e
where e.id_partido = p.id_partido
group by p.id_partido, p.puntos_local, p.puntos_visitante, p.id_equipo_local
having sum(case when e.id_equipo = p.id_equipo_local then e.puntos else 0 end) <> p.puntos_local
    or sum(case when e.id_equipo <> p.id_equipo_local then e.puntos else 0 end) <> p.puntos_visitante;


-- ---------------------------------------------------------------------
-- INFORMATIVO (esta SI devuelve filas)
-- ---------------------------------------------------------------------

-- C30) cuantas veces no se presento cada equipo (W.O.)
select eq.nombre as equipo, count(*) as veces_que_no_se_presento
from partido p, equipo eq
where p.id_equipo_ausente = eq.id_equipo
group by eq.nombre
order by veces_que_no_se_presento desc, eq.nombre;


-- =====================================================================
-- CONSULTAS DE EJEMPLO
-- =====================================================================

-- E1) tabla de posiciones del Apertura U19 (version simple: puntos y diferencia;
--     el desempate FIBA completo va en las consultas complejas de la etapa 2)
select eq.nombre as equipo,
       count(*) as pj,
       sum(case when (p.id_equipo_local = eq.id_equipo and p.puntos_local > p.puntos_visitante)
                  or (p.id_equipo_visitante = eq.id_equipo and p.puntos_visitante > p.puntos_local)
                then 1 else 0 end) as pg,
       sum(case when (p.id_equipo_local = eq.id_equipo and p.puntos_local > p.puntos_visitante)
                  or (p.id_equipo_visitante = eq.id_equipo and p.puntos_visitante > p.puntos_local) then 2
                when p.id_equipo_ausente = eq.id_equipo then 0
                else 1 end) as pts,
       sum(case when p.id_equipo_local = eq.id_equipo then p.puntos_local - p.puntos_visitante
                else p.puntos_visitante - p.puntos_local end) as dif
from partido p, equipo eq, torneo t, categoria ca
where p.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
  and t.nombre = 'Apertura' and ca.nombre = 'U19'
  and p.fase = 'Regular'
  and eq.id_equipo in (p.id_equipo_local, p.id_equipo_visitante)
group by eq.nombre
order by pts desc, dif desc;

-- E2) goleadores de la temporada (top 10, todas las categorias)
select j.apellido, j.nombre, ca.nombre as categoria, count(*) as partidos,
       sum(e.puntos) as puntos, round(avg(e.puntos), 1) as promedio, sum(e.triples) as triples
from estadistica e, jugador j, torneo t, categoria ca
where e.dni_jugador = j.dni_jugador
  and e.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
group by j.dni_jugador, j.apellido, j.nombre, ca.nombre   -- el dni por si hay dos que se llaman igual
order by puntos desc
limit 10;

-- E3) campeones de cada torneo (ganador de la final)
select t.nombre as torneo, ca.nombre as categoria, p.fecha, c.nombre as cancha_neutral,
       case when p.puntos_local > p.puntos_visitante then l.nombre else v.nombre end as campeon,
       l.nombre || ' ' || p.puntos_local || ' - ' || p.puntos_visitante || ' ' || v.nombre as resultado
from partido p, torneo t, categoria ca, equipo l, equipo v, cancha c
where p.fase = 'Final'
  and p.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
  and p.id_equipo_local = l.id_equipo
  and p.id_equipo_visitante = v.id_equipo
  and p.id_cancha = c.id_cancha
order by t.id_torneo;

-- E4) los que "la rompieron": las 10 mejores actuaciones en un partido
select j.apellido, j.nombre, ca.nombre as categoria, p.fecha, e.puntos, e.triples, e.rebotes, e.minutos
from estadistica e, jugador j, partido p, torneo t, categoria ca
where e.dni_jugador = j.dni_jugador
  and e.id_partido = p.id_partido
  and p.id_torneo = t.id_torneo
  and t.id_categoria = ca.id_categoria
order by e.puntos desc
limit 10;
