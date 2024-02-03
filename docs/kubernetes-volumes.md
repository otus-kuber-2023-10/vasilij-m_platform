### Задание 1. Применение StatefulSet
---
**Выполнение**  

Для развертывания MinIO применим манифест `./kubernetes-volumes/minio-statefulset.yaml`:
```bash
kubectl apply -f kubernetes-volumes/minio-statefulset.yaml
```

В результате в кластере будут созданы следующие объекты: 
1. Под `minio-0`
```bash
$ kubectl get pods                                       
NAME      READY   STATUS    RESTARTS   AGE
minio-0   1/1     Running   0          119s
```
2. PVC `data-mino-0`
```bash
$ kubectl get pvc 
NAME           STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-minio-0   Bound    pvc-ffe3c691-5769-47f2-98ed-e13a1b99be89   10Gi       RWO            standard       5m24s
```
3. Динамически создаться PV на этом PVC с помощью дефолотного StorageClass
```bash
$ kubectl get pv 
NAME                                       CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                  STORAGECLASS   REASON   AGE
pvc-ffe3c691-5769-47f2-98ed-e13a1b99be89   10Gi       RWO            Delete           Bound    default/data-minio-0   standard                7m12s
```

### Задание 2. Применение Headless Service
---
**Выполнение**

Для того, чтобы StatefulSet с MinIO был доступен изнутри кластера, создадим Headless Service, применив манифест `./kubernetes-volumes/minio-headless-service.yaml`:
```bash
kubectl apply -f kubernetes-volumes/minio-headless-service.yaml
```
Результат:
```bash
$ kubectl get svc                                        
NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE
kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP    25m
minio        ClusterIP   None         <none>        9000/TCP   20s  
```
  
### Задание 3. Проверка работы MinIO
--- 
**Выполнение**

Проверить работу Minio можно с помощью консольного клиента [mc](https://github.com/minio/mc).

1. Скачаем его бинарь:
```bash
curl -o /tmp/mc https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x /tmp/mc
```

2. Пробросим порт, чтобы можно было подключиться к MinIO снаружи кластера:
```bash
kubectl port-forward service/minio 9000:9000
```
3. Создадим alias для удобства подключения к MinIO:
```bash
$ /tmp/mc alias set myminio http://localhost:9000 minio minio123
Added `myminio` successfully.
```
4. Протестируем соединение:
```bash
$ /tmp/mc admin info myminio
●  localhost:9000
   Uptime: 33 minutes 
   Version: 2023-09-30T07:02:29Z
   Network: 1/1 OK 
   Drives: 1/1 OK 
   Pool: 1 

Pools:
   1st, Erasure sets: 1, Drives per erasure set: 1 

1 drive online, 0 drives offline     
```
5. Создадим бакет и загрузим файл в MinIO:

Содержимое файла:
```bash
$ cat /tmp/minio_test                                                     
This is for MinIO test
```
Создадим бакет:
```bash
$ /tmp/mc mb --with-lock myminio/mydata
Bucket created successfully `myminio/mydata`.
```
Загрузим файл в бакет:
```bash
$ /tmp/mc cp /tmp/minio_test myminio/mydata/
/tmp/minio_test:            23 B / 23 B ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.21 KiB/s 0s
```
Проверим, что файл действительно загрузился:
```bash
$ /tmp/mc ls --recursive --versions myminio/mydata
[2023-10-04 23:42:53 MSK]    23B STANDARD 613164d5-ba48-4699-825a-31369a72bbbf v1 PUT minio_test
```
6. Удалим под minio-0 и убедимся, что после его пересоздания наш файл будет на месте:
```bash
$ kubectl delete pod minio-0
pod "minio-0" deleted
$ kubectl get pod           
NAME      READY   STATUS    RESTARTS   AGE
minio-0   1/1     Running   0          61s
```
Под пересоздался с тем же именем, проверим, что файл на месте.  
Сначала заново пробросим порт:
```bash
kubectl port-forward service/minio 9000:9000
```
Проверим файл:
```bash
$ /tmp/mc ls --recursive --versions myminio/mydata
[2023-10-04 23:42:53 MSK]    23B STANDARD 613164d5-ba48-4699-825a-31369a72bbbf v1 PUT minio_test
```
Скопируем файл к себе на localhost:
```bash
$ /tmp/mc cp myminio/mydata/minio_test /tmp/from_minio_test
...:9000/mydata/minio_test: 23 B / 23 B ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.13 KiB/s 0s
```
Проверим сдержимое файла:
```bash
$ cat /tmp/from_minio_test
This is for MinIO test
```

### Задание 4 со *. Поместите данные в и настройте конфигурацию на их использование.
--- 
**Выполнение**
  
1. Создадим Secret с именем пользователя и паролем для аутентификации в MinIO, применив манифест `./kubernetes-volumes/minio-secret.yaml`:
```bash
kubectl apply -f kubernetes-volumes/minio-secret.yaml
```
2. Далее вместо блока `env` в спецификации контейнера добавим блок `envFrom` со ссылкой на имя созданного в предыдущем пункте секрета:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: minio
...
spec:
  ...
  template:
    ...
    spec:
      containers:
        - name: minio
          envFrom:
            - secretRef:
                name: minio-auth
      ...
```
3. После удаления и создания StatefulSet `minio` заново, мы все также имеем доступ к MinIO с ранее добавленными кредами:
```bash
$ /tmp/mc admin info myminio                               
●  localhost:9000
   Uptime: 24 seconds 
   Version: 2023-09-30T07:02:29Z
   Network: 1/1 OK 
   Drives: 1/1 OK 
   Pool: 1

Pools:
   1st, Erasure sets: 1, Drives per erasure set: 1

23 B Used, 1 Bucket, 1 Object, 1 Version
1 drive online, 0 drives offline
```
