# Resume (extracted)

AKSHANT  SHARMA Engineer   ·   Distributed  Systems   ·   AI  Infrastructure Bengaluru,  India  ·   +91  9592948889  ·     ·   Akshant3@gmail.com  ·   Linkedin  ·   Github  ·   Profile  ·   Blogs    Akshant Sharma  
SUMMARY 
Staff  Engineer  with  7.5  years  building  the  infrastructure  layer  underneath  —  event  pipelines,  storage  engines,  and  distributed  
systems
 
at
 
load
 
most
 
tools
 
weren't
 
designed
 
for.
 
Contributed
 
to
 
Agoda's
 
WhiteFalcon
 
TSDB
 
(1.5T
 
events/day,
 
Rust
 
+
 
Kafka
 
+
 
Ceph),
 
led
 
two
 
engineering
 
teams
 
at
 
Wayfair
 
shipping
 
a
 
real-time
 
global
 
pricing
 
engine
 
across
 
250k+
 
SKUs
 
per
 
supplier,
 
built
 
geospatial
 
tracking
 
at
 
5k
 
events/sec
 
at
 
Delivery
 
Hero
,
 
and
 
architected
 
7M+
 
sensor
 
ingestion
 
at
 
Walmart
 
Labs
 
on
 
Azure
 
IoT
 
Hub.
 
Currently
 
building
 
open-source
 
AI
 
inference
 
observability
 
tooling
 
in
 
Rust.
 
TECHNICAL  SKILLS Languages:   Java  (High-Concurrency  Expert)   ·   Rust   ·   Go   ·   Scala   ·   Python Distributed  Systems:   Kafka  (internals,  partition  strategy,  backpressure)   ·   Ceph   ·   Redis   ·   ClickHouse Storage  &  Data:   BigQuery   ·   PostgreSQL   ·   MongoDB   ·   Azure  Cosmos  DB   ·   Parquet  /  S3 Cloud  &  Infra:   Kubernetes   ·   Terraform   ·   Helm   ·   AWS  EKS   ·   GCP   ·   Azure  IoT  Hub Observability:   OpenTelemetry   ·   Prometheus   ·   Grafana   ·   ELK  Stack   ·   Distributed  Tracing AI  Inference  &  Tools:   LLM  inference  pipelines   ·   AI  observability   ·   Cursor   ·   GitHub  Copilot   ·   Claude 
CURRENT  PROJECT 
infra-ai-streaming  ·   Open  Source   ·   In  Progress Rust  ingestion  engine  →  Kafka  →  Go  consumer  →  ClickHouse  →  Grafana •  High-throughput  AI  inference  observability  pipeline  for  LLM  metrics  (latency,  token  cost,  anomaly  detection)  built  for  the  
metric
 
cardinality
 
and
 
event
 
volume
 
that
 
standard
 
monitoring
 
tools
 
break
 
under.
 •  Axum  HTTP  server,  WAL  durability,  per-tenant  rate  limiting,  circuit  breaker  with  Redis  overflow  buffer,  Z-score  anomaly  
detection,
 
Helm
 
+
 
HPA
 
scaling
 
on
 
Kafka
 
consumer
 
lag.
 
Target:
 
1M
 
events/min
 
at
 
<100ms
 
P99.
 
PROFESSIONAL  EXPERIENCE 
Wayfair  ·   Bengaluru Nov  2024  –  Mar  2026 Sr.  Software  Engineer  III   ·   Led  PAS  &  Pricing  Promotion  Teams 
•  Led  PAS  and  Pricing,  Promotions  &  Discounts  teams  —  owning  end-to-end  delivery  across  both  product  areas  
simultaneously;
 
architected
 
a
 
GCP
 
event-driven
 
Global
 
Pricing
 
&
 
Promotion
 
Engine
 
reducing
 
price
 
propagation
 
from
 
hours
 
to
 
sub-seconds
 
across
 
20k+
 
suppliers.
 •  250k+  SKU  updates  per  supplier  in  near  real-time :  Engineered  a  high-throughput  bulk  processing  framework  (99.99%  
availability)
 
with
 
distributed
 
rate
 
limiting
 
and
 
circuit
 
breakers,
 
eliminating
 
degradation
 
and
 
cascading
 
failures
 
under
 
peak
 
global
 
load.
  
Agoda  ·   Bangkok Apr  2024  –  Sep  2024 Sr.  Software  Engineer  ·   Core  Infrastructure  ·  WhiteFalcon  TSDB 
•  1.5  trillion  events/day  TSDB :  Contributed  to  WhiteFalcon,  Agoda's  in-house  Rust  +  Scala  TSDB  on  Kafka  —  higher  
ingestion
 
cardinality
 
than
 
any
 
off-the-shelf
 
TSDB
 
supports;
 
extended
 
query
 
engine
 
for
 
cross-tier
 
Redis/S3
 
queries,
 
solving
 
the
 
quantile
 
merge
 
problem
 
to
 
enable
 
correct
 
P95/P99
 
across
 
arbitrary
 
time
 
ranges.
 •  Cardinality-safe  Kubernetes  indexing  +  15–20%  storage  reduction :  Extended  the  RoaringBitmap  inverted  index  to  cover  
K8s
 
dimensions
 
(modifying
 
Rust
 
ingestion
 
+
 
series
 
ID
 
generation)
 
to
 
prevent
 
index
 
explosion;
 
migrated
 
cold-tier
 
Parquet
 
compression
 
from
 
Snappy
 
to
 
Zstd
 
with
 
<1%
 
read
 
latency
 
impact.
  
Delivery  Hero  ·   Berlin Jun  2022  –  Jul  2023 Sr.  Software  Engineer   ·   Global  Logistics  Platform 
•  1M+  daily  orders   ·   5k  map  adjustments/sec :  Scaled  logistics  platform  to  1M+  daily  orders  on  AWS  EKS  (10k+  concurrent  
requests,
 
zero
 
downtime);
 
built
 
end-to-end
 
rider
 
tracking
 
using
 
OSRM
 
processing
 
5k+
 
real-time
 
route
 
updates/sec.
 •  Cascading  failure  elimination :  Designed  async  SQS  +  Kinesis  pipeline  decoupling  order  processing  from  notifications,  
guaranteeing
 
sub-second
 
delivery
 
status
 
updates
 
for
 
millions
 
of
 
active
 
users
 
at
 
peak.
  
BrowserStack  ·   Mumbai May  2021  –  Dec  2021 Sr.  Software  Engineer   ·   Device  Instrumentation 
•  Reverse-engineered  APKs/IPAs  to  hook  into  native  iOS/Android  OS  APIs,  enabling  fully  automated  FaceID/TouchID  testing  
on
 
remote
 
physical
 
devices
 
via
 
Camera
 
Image
 
Injection
 
and
 
Biometrics
 
instrumentation.
  
Walmart  Labs  ·   Bengaluru Aug  2018  –  May  2021 Software  Engineer  II   ·   WeIoT  SmartBuildings  Platform   ·   3  years 
•  7M+  sensors,  tens  of  millions  of  telemetry  points/min :  Architected  WeIoT  SmartBuildings  ingestion  layer  on  Azure  IoT  
Hub;
 
engineered
 
real-time
 
HVAC
 
control
 
loops
 
via
 
Azure
 
Stream
 
Analytics
 
automating
 
energy
 
optimisation
 
across
 
50+
 
global
 
facilities.
 •  Fault-tolerant  edge-to-cloud  OTA  firmware  framework  —  reliable  config  syncs  and  updates  for  millions  of  distributed  
devices
 
under
 
intermittent
 
network
 
conditions.
  
Integration  Wizards  ·   Bengaluru Mar  2017  –  Aug  2018 IoT  Lead   ·   Industrial  IoT  Platform 
•  Industrial  IIoT  platform  for  Dover  USA :  Ingestion  backbone  for  oil  well  and  compressor  telemetry  with  100%  data  
delivery
 
in
 
low-bandwidth
 
environments;
 
edge-compute
 
preprocessing
 
to
 
filter
 
and
 
aggregate
 
locally
 
before
 
cloud
 
transmission.
 
EDUCATION 
B.E.  Computer  Science  ·   Chandigarh  UniversityGPA  7.2  /  10 Diploma,  Electrical  Engineering  ·   CCET  Chandigarh 
CERTIFICATIONS 
Microsoft  Certified:  Azure  Fundamentals  ·   Employee  of  the  Year  —  Integration  Wizards 