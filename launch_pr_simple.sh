#!/usr/bin/env fish
cd /home/sergio/src/tfm/burst-validation/pagerank
source ../.venv/bin/activate.fish
set -x PYTHONPATH /home/sergio/src/tfm/burst-validation

echo "🚀 Lanzando PageRank en OpenWhisk..."
echo "⏳ Compilación de Rust tomará ~50-60 segundos..."
echo ""

python3 pagerank.py \
  --ow-host localhost \
  --ow-port 31001 \
  --pr-endpoint http://minio-service.default:9000 \
  --partitions 4 \
  --num-nodes 5 \
  --bucket test-bucket \
  --key graphs/pagerank \
  --granularity 4 \
  --backend redis-list \
  --chunk-size 1048576 \
  --custom-image burstcomputing/runtime-rust-burst:latest \
  --join true

if test $status -eq 0
  echo ""
  echo "✅ PageRank completado!"
  echo "📊 Resultados en pagerank-burst.json"
else
  echo ""
  echo "❌ Error en la ejecución"
end
