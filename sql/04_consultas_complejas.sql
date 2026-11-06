-- =====================================================================
-- TP Final Parte 2 - Base de Datos
-- 04_consultas_complejas.sql: las 6 consultas complejas (+ 2 de yapa)
-- Integrantes: Tomiozzo Franco y Schmidt Gonzalo
-- Correr DESPUES de 01 y 02. Las usa tambien el dashboard (app-dashboard).
-- =====================================================================
-- Formato: cada consulta arranca con "-- Qn) titulo" y abajo, en otra
-- linea "-- Usa:", los operadores que muestra (join, exists, in, etc.).
-- =====================================================================


-- Q1) Tabla de posiciones de cada torneo (fase regular), con W.O. incluidos
-- Usa: join de 4 tablas, case when, group by, in (eq en local o visitante)
select t.nombre as torneo, ca.nombre as categoria, eq.nombre as equipo,
       count(*) as pj,
       sum(case when (p.id_equipo_local = eq.id_equipo and p.puntos_local > p.puntos_visitante)
                  or (p.id_equipo_visitante = eq.id_equipo and p.puntos_visitante > p.puntos_local)
                then 1 else 0 end) as pg,
       sum(case when (p.id_equipo_local = eq.id_equipo and p.puntos_local < p.puntos_visitante)
                  or (p.id_equipo_visitante = eq.id_equipo and p.puntos_visitante < p.puntos_local)
                then 1 else 0 end) as pp,
       sum(case when p.id_equipo_ausente = eq.id_equipo then 1 else 0 end) as wo,
       sum(case when (p.id_equipo_local = eq.id_equipo and p.puntos_local > p.puntos_visitante)
                  or (p.id_equipo_visitante = eq.id_equipo and p.puntos_visitante > p.puntos_local) then 2
                when p.id_equipo_ausente = eq.id_equipo then 0
                else 1 end) as pts,
       sum(case when p.id_equipo_local = eq.id_equipo then p.puntos_local else p.puntos_visitante end) as pf,
       sum(case when p.id_equipo_local = eq.id_equipo then p.puntos_visitante else p.puntos_local end) as pc,
       sum(case when p.id_equipo_local = eq.id_equipo then p.puntos_local - p.puntos_visitante
                else p.puntos_visitante - p.puntos_local end) as dif
from partido p
join torneo t on t.id_torneo = p.id_torneo
join categoria ca on ca.id_categoria = t.id_categoria
join equipo eq on eq.id_equipo in (p.id_equipo_local, p.id_equipo_visitante)
where p.fase = 'Regular'
group by t.id_torneo, t.nombre, ca.nombre, eq.id_equipo, eq.nombre
order by t.id_torneo, pts desc, dif desc;


-- Q2) Los jugadores que tuvieron un pase: como les fue antes y despues
--     (promedio de puntos en el Apertura con el club de origen y en el
--     Clausura con el club de destino)
-- Usa: join, in con subconsulta, subconsultas correlacionadas en el select
select j.apellido, j.nombre, ca.nombre as categoria,
       eo.nombre as equipo_origen, ed.nombre as equipo_destino,
       (select round(avg(e.puntos), 1) from estadistica e, torneo t
         where e.dni_jugador = pa.dni_jugador and e.id_equipo = pa.id_equipo_origen
           and e.id_torneo = t.id_torneo and t.nombre = 'Apertura') as prom_apertura,
       (select round(avg(e.puntos), 1) from estadistica e, torneo t
         where e.dni_jugador = pa.dni_jugador and e.id_equipo = pa.id_equipo_destino
           and e.id_torneo = t.id_torneo and t.nombre = 'Clausura') as prom_clausura
from pase pa
join jugador j on j.dni_jugador = pa.dni_jugador
join equipo eo on eo.id_equipo = pa.id_equipo_origen
join equipo ed on ed.id_equipo = pa.id_equipo_destino
join categoria ca on ca.id_categoria = eo.id_categoria
where pa.dni_jugador in (select pl.dni_jugador from plantel pl, torneo t
                         where pl.id_torneo = t.id_torneo and t.nombre = 'Clausura'
                           and pl.id_equipo = pa.id_equipo_destino)
order by ca.nombre, j.apellido;


-- Q3) Equipos que ganaron TODOS los partidos que jugaron de local en la
--     fase regular de un torneo ("invictos en casa")
-- Usa: not exists (no existe un partido de local que hayan perdido)
select t.nombre as torneo, ca.nombre as categoria, eq.nombre as equipo,
       (select count(*) from partido p
         where p.id_torneo = t.id_torneo and p.fase = 'Regular'
           and p.id_equipo_local = eq.id_equipo) as partidos_de_local
from equipo eq
join torneo t on t.id_categoria = eq.id_categoria
join categoria ca on ca.id_categoria = t.id_categoria
where not exists (select 1 from partido p
                  where p.id_torneo = t.id_torneo
                    and p.fase = 'Regular'
                    and p.id_equipo_local = eq.id_equipo
                    and p.puntos_local < p.puntos_visitante)
order by t.id_torneo, eq.nombre;


-- Q4) Arbitros que dirigieron en TODAS las canchas de la liga
--     (division relacional: no existe una cancha en la que no hayan estado)
-- Usa: doble not exists (division), subconsulta en el select
select a.apellido, a.nombre, a.categoria_arbitro,
       (select count(*) from arbitro_partido ap
         where ap.dni_arbitro = a.dni_arbitro and ap.asistencia <> 'Ausente') as partidos
from arbitro a
where not exists (select 1 from cancha c
                  where not exists (select 1
                                    from arbitro_partido ap, partido p
                                    where ap.dni_arbitro = a.dni_arbitro
                                      and ap.asistencia <> 'Ausente'
                                      and ap.id_partido = p.id_partido
                                      and p.id_cancha = c.id_cancha))
order by partidos desc;


-- Q5) Jugadores que promedian MAS DEL DOBLE que el promedio de su
--     categoria y ademas jugaron un playoff (cuartos, semis o final)
-- Usa: having con subconsulta correlacionada, exists
select j.apellido, j.nombre, ca.nombre as categoria, j.posicion,
       count(*) as partidos, round(avg(e.puntos), 1) as promedio
from estadistica e
join jugador j on j.dni_jugador = e.dni_jugador
join torneo t on t.id_torneo = e.id_torneo
join categoria ca on ca.id_categoria = t.id_categoria
where exists (select 1 from estadistica e2, partido p
              where e2.dni_jugador = e.dni_jugador
                and e2.id_partido = p.id_partido
                and p.fase <> 'Regular')
group by j.dni_jugador, j.apellido, j.nombre, ca.id_categoria, ca.nombre, j.posicion
having avg(e.puntos) > (select avg(e3.puntos) * 2
                        from estadistica e3, torneo t3
                        where e3.id_torneo = t3.id_torneo
                          and t3.id_categoria = ca.id_categoria)
order by ca.nombre, promedio desc;


-- Q6) Clubes que metieron a sus 4 categorias en el playoff de un mismo
--     torneo (Apertura o Clausura)
-- Usa: not exists + in (no hay un equipo del club que no este en cuartos)
select distinct c.nombre as club, t.nombre as torneo
from club c, torneo t
where not exists (select 1 from equipo eq, torneo t2
                  where eq.id_club = c.id_club
                    and t2.nombre = t.nombre and t2.temporada = t.temporada
                    and t2.id_categoria = eq.id_categoria
                    and eq.id_equipo not in (select s.id_equipo_mejor from serie s
                                             where s.id_torneo = t2.id_torneo and s.fase = 'Cuartos'
                                             union
                                             select s.id_equipo_peor from serie s
                                             where s.id_torneo = t2.id_torneo and s.fase = 'Cuartos'))
order by t.nombre, c.nombre;


-- Q7) Entrenadores campeones: quien dirigia al equipo que gano cada final
-- Usa: join de 6 tablas, case when para sacar el ganador
select t.nombre as torneo, ca.nombre as categoria, eq.nombre as campeon,
       en.apellido || ', ' || en.nombre as entrenador, en.nivel_eneba,
       p.puntos_local || ' - ' || p.puntos_visitante as resultado, c.nombre as cancha
from partido p
join torneo t on t.id_torneo = p.id_torneo
join categoria ca on ca.id_categoria = t.id_categoria
join cancha c on c.id_cancha = p.id_cancha
join equipo eq on eq.id_equipo = case when p.puntos_local > p.puntos_visitante
                                      then p.id_equipo_local else p.id_equipo_visitante end
join entrenador en on en.dni_entrenador = eq.dni_entrenador
where p.fase = 'Final'
order by t.id_torneo;


-- Q8) Partidos con algo raro: postergados, W.O. o con un arbitro ausente
-- Usa: union de 3 consultas, exists
select p.id_partido, p.fecha, ca.nombre as categoria, 'Postergado' as que_paso,
       p.motivo_postergacion as detalle
from partido p, torneo t, categoria ca
where p.id_torneo = t.id_torneo and t.id_categoria = ca.id_categoria
  and p.fecha_original is not null
union
select p.id_partido, p.fecha, ca.nombre, 'W.O.', eq.nombre || ' no se presento'
from partido p, torneo t, categoria ca, equipo eq
where p.id_torneo = t.id_torneo and t.id_categoria = ca.id_categoria
  and p.id_equipo_ausente = eq.id_equipo
union
select p.id_partido, p.fecha, ca.nombre, 'Arbitro ausente', ap.observacion
from partido p, torneo t, categoria ca, arbitro_partido ap
where p.id_torneo = t.id_torneo and t.id_categoria = ca.id_categoria
  and ap.id_partido = p.id_partido and ap.asistencia = 'Ausente'
  and exists (select 1 from arbitro_partido s
              where s.id_partido = p.id_partido and s.rol = 'Suplente')
order by fecha;
