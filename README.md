!#Introducción


__Rebost__ debe ser el gestor de software del sistema. Debe encargarse de todo lo relacionado con la gestión del mismo, desde la gestión de repositorios hasta la instalación de aplicaciones en los equipos del aula.
Para ello se va a trabajar en la integración entre las distintas herramientas que ofrece LliureX para este tipo de tareas


!#Fase 1


En esta primera fase se trabajará sobre la integración de servicios en LliureX Store así como en facilitar una api de LliureX Store que nos permita integrar la gestión del catálogo de software en las aplicaciones que lo requieran. A día de hoy el instalador EPI utiliza la api de la tienda para extraer información sobre los programas a instalar, la idea es extender esta api de forma que permita ya no solo extraer información sino integrar por completo los servicios de la store dentro de las aplicaciones que requieran interactuar con el software del sistema. Por ejemplo repoman ya no gestionaria los repositorios, de ello se encargaría la api de __rebost__ y repoman únicamente se encargaria de mostrar la información en pantalla.


!!#Estructura de la Fase 1


Si entendemos el proceso de gestión de software mediante herramientas de LliureX como un proceso lineal ordenado encontraríamos que:


*Repoman (Gestión de repos) -> LliureX Store (búsqueda de software) -> EPI (instalación de software)*


Debería ser la secuencia habitual de este proceso pero sin embargo encontramos demasiadas bifurcaciones que hacen que dicha secuencia no se cumpla prácticamente nunca. Así pues es necesario abordar el problema desde otra perspectiva.
La aquí propuesta pasaria por un nucleo central, *rebost*, encargado de distribuir las operaciones a realizar entre los distintos agentes que ya forman parte del sistema.

En esta fase 1 el objetivo es pulir la experiencia de uso de las actuales herramientas usadas.


!!#Lliurex Store


* Implementar un sistema de tickets para cada operación realizada. Actualmente funciona por acciones, rebost debe implementar un sistema de colas y para ello es necesario cambiar el funcionamiento actual por un sistema de tickets
* Mejorar la gestión de errores
* Implementar el manejo de catálogos externos (via git)
* Implementar un icono en la barra de tareas que informe al usuario del transcurso de las operaciones y permita realizar búsquedas sin ejecutar la store
* Crear un demonio de systemd encargado de gestionar la caché de la store (actualmente solo se ejecuta al lanzar la store)
* Requiere agilizar la velocidad de las operaciones, sobre todo a la hora de trabajar con los catálogos de snap y appimage (solventado con la caché). 
* Realizar los cambios necesarios en la api (de ser necesarios) para que el catálogo pueda integrarse en otras aplicaciones (p.e. Zero-Center)
* Integrar con Lliurex Remote Installer
* Cambios en la GUI para ajustarla a la temática general del sistema


!# Fase 2


Esta segunda fase consistira en aplicar los cambios realizados a las distintas herramientas ya existente para conseguir la cohesión de la gestión del software del sistema.
Sería necesario modificar las aplicaciones existentes para usar y ser usadas desde rebost.


!!#EPI


* Añadir soporte para snap, appimage y air de forma que sea el instalador genérico que *requeriría* rebost
* Posiblemente agregar una api que permita la interacción externa


!!#Remote Installer


* Delegar en rebost la instalación del software (lo que añadiría soporte a todos los tipos de paquetes soportados por rebost)


!!#AppimageManager y AirManager


* Integrarse como plugins de rebost.


!!#RepoMan


* Delegar la gestión de repositorios a rebost. 
* Integrar la aplicación como plugin de rebost.


!!#Zero-Center


* Obtener los zomandos desde el catálogo de la store
* Delegar la instalación de los mismos a rebost

