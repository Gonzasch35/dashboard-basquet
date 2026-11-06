-- =====================================================================
-- TP Final Parte 2 - Base de Datos
-- 05_algebra_relacional.sql: consulta de 3 tablas con una condicion de
-- igualdad y una de rango, antes y despues de optimizar el arbol
-- Integrantes: Tomiozzo Franco y Schmidt Gonzalo
-- =====================================================================
-- Pregunta: que jugadores hicieron 25 puntos o mas en un partido de
-- semifinal (y en que fecha).
--   Tablas:     jugador (J), estadistica (E), partido (P)
--   Igualdad:   P.fase = 'Semifinal'
--   Rango:      E.puntos >= 25
--
-- Arbol inicial (como sale de leer el SQL tal cual):
--   pi apellido, nombre, fecha, puntos (
--     sigma J.dni = E.dni AND E.id_partido = P.id_partido
--           AND P.fase = 'Semifinal' AND E.puntos >= 25 (
--       (J x E) x P ))
--
-- Arbol optimizado (selecciones lo mas abajo posible, productos
-- cartesianos + seleccion -> join, y proyecciones tempranas):
--   pi apellido, nombre, fecha, puntos (
--     ( pi dni, apellido, nombre (J)
--       join_{J.dni = E.dni}
--       pi dni, id_partido, puntos ( sigma puntos >= 25 (E) ) )
--     join_{E.id_partido = P.id_partido}
--     pi id_partido, fecha ( sigma fase = 'Semifinal' (P) ) )
-- =====================================================================


-- A1) Consulta original (producto cartesiano y todas las condiciones en el where)
select j.apellido, j.nombre, p.fecha, e.puntos
from jugador j, estadistica e, partido p
where j.dni_jugador = e.dni_jugador
  and e.id_partido = p.id_partido
  and p.fase = 'Semifinal'
  and e.puntos >= 25
order by e.puntos desc;


-- A2) Consulta escrita a partir del arbol optimizado: primero se filtra
--     cada tabla y se quedan solo las columnas que hacen falta, y despues
--     se juntan los resultados chicos
select jj.apellido, jj.nombre, pp.fecha, ee.puntos
from (select dni_jugador, apellido, nombre from jugador) jj
join (select dni_jugador, id_partido, puntos from estadistica
      where puntos >= 25) ee on jj.dni_jugador = ee.dni_jugador
join (select id_partido, fecha from partido
      where fase = 'Semifinal') pp on ee.id_partido = pp.id_partido
order by ee.puntos desc;
