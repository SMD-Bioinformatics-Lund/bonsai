Bonsai developer documentation
==============================

Overview of the Bonsai software stack.

.. graphviz:: 
    :caption: Overview of Bonsai software stack.

    digraph bonsai {
        rankdir="LR";
        
        edge [dir=both]

        user [shape=Msquare; label=User]
        
        mongo_db [shape=cylinder; style=filled; fillcolor="#84ba5f"; label=MongoDb]
        redis_db [shape=cylinder; style=filled; fillcolor="#dc382c"; label=Redis]
        
        frontend [shape=box; label=Frontend]
        api [shape=box; label=API]
        minhash [shape=box; label="MinHash\nservice"]
        cluster [shape=box; label="Allele cluster\nservice"]
        
        signatures [shape=note; style="filled"; fillcolor="lightgrey"; label="Signature\nfiles"]
        
        
        // arrows
        user -> frontend -> api

        api -> mongo_db
        api -> redis_db -> minhash -> signatures
        redis_db -> cluster
    }
