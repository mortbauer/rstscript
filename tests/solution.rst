:title: Berechnung des Dampf-Flüssigkeits-Gleichgewichts
:date: 19 Jänner 2013

Für das Binäre Stickstoff Methan Gemisch soll der Druck und die Dampfphasen
Zusammensetzung berechnet werden.


.. code:: python



Dies kann wohl ganz gerade gelöst werden einfach naeinander alle Koeffizienten
berechen:


.. code:: python



Wobei erst einmal die Koeffizienten der Reinstoffe berechnet werden müssen:


.. code:: python



Nun kann man die Gemischparameter der Soave Redlich Kwong Gleichung auswerten:


.. code:: python



Diese Koeffizienten gelten sowohl für die flüssige als auch die gasförmige
Phase, die anderen Koeffizienten müssen sowohl für die flüssige als auch die
gasförmige Phase separat berechnet werden.


.. code:: python



Um ein Volumen zu berechnen muss iterativ vorgegangen werden, da ja weder v
noch p bekannt sind:


.. code:: python




