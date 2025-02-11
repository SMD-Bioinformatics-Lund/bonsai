Bonsai developer documentation
==============================

Bonsai consists of a front end, an API layer, and several services that perform long-running or computationally intensive tasks. The front end uses the API to query or update the database and to create jobs for the services to execute. Redis is used as a queue and for caching the results of API queries. The services listen for submitted jobs, perform the task, and return the results to Redis. The front end can then request status updates of submitted jobs using the unique job id it received when it requested the job.

.. graphviz:: 
    :caption: Overview of Bonsai software stack.

    digraph bonsai {
        rankdir="LR";
        
        edge [dir=both]

        user [shape=Msquare; label=User]
        
        mongo_db [shape=cylinder; style=filled; fillcolor="#84ba5f"; label=MongoDb]
        redis_db [shape=cylinder; style=filled; fillcolor="#dc382c"; label=Redis]
        
        frontend [shape=box; label="Front end"]
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


Services
--------

.. toctree::

    frontend
    minhash
    allele_clustering