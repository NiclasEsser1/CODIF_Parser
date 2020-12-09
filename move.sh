while getopts a:n:d option
do
case "${option}"
in
a) DATE=${OPTARG};;
esac
done


ROOT_DIR="/beegfsEDD/NESSER"
NOF_NODES=16

mkdir $ROOT_DIR/$DATE

for i in $(seq 0 $(($NOF_NODES-1)))
do
  mkdir $ROOT_DIR/$DATE/numa$i/
  mv $ROOT_DIR/numa$i/$DATE* $ROOT_DIR/$DATE/numa$i/
done
