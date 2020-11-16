while getopts a:w:n:c:o option
do
case "${option}"
in
a) ETH_NAME=${OPTARG};;
w) START_PORT=${OPTARG};;
n) NOF_PORT=${OPTARG};;
c) NUMBER_PACKETS=${OPTARG};;
o) OUTPUT=${OPTARG};;
esac
done

mkdir -p tmp/

for i in $(seq 0 $(($NOF_PORT-1)))
do
    PORT=$(($START_PORT+$i))
    tcpdump -i $ETH_NAME '"'port $PORT'"' -c $NUMBER_PACKETS -w '"'tmp/$PORT.pcap'"'
    python python/codif_parse.py -f tmp/$PORT.pcap -o $ETH_NAME$PORT.txt
done

rm -R tmp/

