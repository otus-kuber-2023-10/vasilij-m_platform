### Задание 1. Подготовка, CustomResource и CustomResourceDefinition
---
**Выполнение**  

>ℹ️ **NOTE**  
>  Для выполнения данной работы на `minikube` при его запуске необходимо включить валидацию кастомных ресурсов, иначе такие ресурсы при создании не будут провалидированы на наличие обязательных полей в спецификации:  
`minikube start --kubernetes-version=v1.27.10 --feature-gates=CustomResourceValidationExpressions=true`

1. В манифесте `./kubernetes-operators/deploy/crd.yaml` описан `CustomResourceDefinition` `mysqls.otus.homework`, после его применения мы сможем создавать в кластере ресурсы с kind `MySQL`, обращаясь к API `otus.homework/v1`. В манифесте `./kubernetes-operators/deploy/cr.yaml` как раз описан такой ресурс `MySQL`.
2. Применим CRD и CR:
```bash
$ kubectl apply -f kubernetes-operators/deploy/crd.yaml
customresourcedefinition.apiextensions.k8s.io/mysqls.otus.homework created
$
$ kubectl apply -f kubernetes-operators/deploy/cr.yaml 
mysql.otus.homework/mysql-instance created
$
$ kubectl describe mysqls.otus.homework mysql-instance      
Name:         mysql-instance
Namespace:    default
Labels:       <none>
Annotations:  <none>
API Version:  otus.homework/v1
Kind:         MySQL
Metadata:
  Creation Timestamp:  2024-02-04T16:08:53Z
  Generation:          1
  Resource Version:    2873
  UID:                 1f6e43b9-5c8a-4514-8620-9f158cb2e47f
Spec:
  Database:      otus-database
  Image:         mysql:5.7
  Password:      otuspassword
  storage_size:  1Gi
Events:          <none>
```

### Задание 2. MySQL оператор | Разработка контроллера
---
**Описание**

Оператор включает в себя `CustomResourceDefinition` и `сustom сontroller`:
- CRD содержит описание объектов CR (CRD мы уже создали в предыдущем пункте)
- Контроллер следит за объектами определенного типа, и осуществляет всю логику работы оператора

Контроллер будет обрабатывать два типа событий:
1. При создании объекта c kind `MySQL`, он будет:
   1. Cоздавать `PersistentVolume`, `PersistentVolumeClaim`, `Deployment`, `Service` для mysql
   2. Создавать `PersistentVolume`, `PersistentVolumeClaim` для бэкапов базы данных, если их еще нет
   3. Пытаться восстановиться из бэкапа
2. При удалении объекта c kind `MySQL`, он будет:
   1. Удалять все успешно завершенные `backup-job` и `restore-job`
   2. Удалять `PersistentVolume`, `PersistentVolumeClaim`, `Deployment`, `Service` для mysql

**Выполнение**

1. Создадим виртуальное окружение в директории ./kubernetes-operators/build и установим необходимые пакеты:
```bash
$ cd kubernetes-operators/build
$ python3 -m venv venv
$ # или source ./venv/bin/activate для активации ранее созданного venv
$ pip3 install -r requirements.txt
```
2. Код нашего оператора (MySQL оператора) написан в файле `./kubernetes-operators/build/mysql-operator.py`
3. В дирректории `./kubernetes-operators/build/templates` находятся шаблоны манифестов ресурсов, которые будут созданы оператором
4. Если запустить файл `./kubernetes-operators/build/mysql-operator.py` с помощью `kopf` (Kubernetes Operator Pythonic Framework), то в логах мужно увидеть, что успешно отработал хендлер `mysql_on_create`:
```bash
$ kopf run mysql-operator.py
/selfup/cources/Otus/kubernetes/vasilij-m_platform/kubernetes-operators/build/venv/lib/python3.10/site-packages/kopf/_core/reactor/running.py:179: FutureWarning: Absence of either namespaces or cluster-wide flag will become an error soon. For now, switching to the cluster-wide mode for backward compatibility.
  warnings.warn("Absence of either namespaces or cluster-wide flag will become an error soon."
[2024-02-04 22:40:55,310] kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
[2024-02-04 22:40:55,339] kopf.activities.auth [INFO    ] Activity 'login_via_client' succeeded.
[2024-02-04 22:40:55,340] kopf._core.engines.a [INFO    ] Initial authentication has finished.
[2024-02-04 22:40:55,539] kopf.objects         [INFO    ] [default/mysql-instance] Handler 'mysql_on_create' succeeded.
[2024-02-04 22:40:55,540] kopf.objects         [INFO    ] [default/mysql-instance] Creation is processed: 1 succeeded; 0 failed.
```

В этом же логе видно, что успешно создался объект `mysql-instance`, хотя он уже был создан ранее.

***Вопрос:*** Почему объект создался, хотя мы создали CR, до того, как запустили оператор?  
***Ответ***: В документации kopf, написано, что оператор обрабатывает объекты, которые были созданы до его запуска в кластере ([ссылка](https://kopf.readthedocs.io/en/stable/walkthrough/starting/#starting-the-operator)).  
Если повторно перезапустить оператор, то события обработки ранее созданных объектов в логе оператора не появится.  
Если сравнить манифест `mysql-instance`, хранящийся в кластере до деплоя оператора и после, то отличие будет в добавлении аннотации `kopf.zalando.org/last-handled-configuration`, видимо, в этом и ответ `:)`. То есть обработка ранее созданного объекта в нашем случае заключалась в добавлении этой аннотации:
```yaml
  annotations:
    kopf.zalando.org/last-handled-configuration: |
      {"spec":{"database":"otus-database","image":"mysql:5.7","password":"otuspassword","storage_size":"1Gi"}}
```
5. Для удаления связанных с ресурсом `mysqls.otus.homework` ресурсов `deployment`, `svc`, `pv` и `pvc` можно использовать декоратор `@kopf.on.delete()`, либо (что более удобно) сделать эти ресурсы дочерними к ресурсу `mysqls.otus.homework` (строки 91-94 в файле `./kubernetes-operators/build/mysql-operator.py`).
6. В строках 104-116 добавлено создание `pv` и `pvc` для бэкапов. Обработка исключений здесь нужна, чтобы контроллер не пытался бесконечно пересоздавать `pv` и `pvc`, т.к. их жизненный цикл отличен от жизненного цикла `mysql`.
7. Создание бэкапов и восстановление из них реализовано с помощью `jobs`.  
К тому же нам нужно удалять законченные `jobs` с определенным именем, так как повторно их запускать нельзя. Эта логика удаления реализована в функции `delete_success_jobs()`.  
Также добавлена функция `wait_until_job_end()` для ожидания завершения `backup job`, чтобы дождаться пока backup выполнится перед удалением `mysql deployment`, `svc`, `pv`, `pvc`.  
8. Запускаем оператор (из директории `./kubernetes-operators/build`) и создаем CR:
```bash
$ kopf run mysql-operator.py
$ kubectl apply -f kubernetes-operators/deploy/cr.yaml
mysql.otus.homework/mysql-instance created
```
9. Проверяем что появились `pvc`:
```bash
$ kubectl get pvc
NAME                        STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
backup-mysql-instance-pvc   Bound    pvc-0dfc030d-bdff-48ee-a860-b946536592b3   1Gi        RWO            standard       3m33s
```
10. Проверим, что все работает, для этого заполним базу созданного `mysql-instance`:
```bash
$ export MYSQLPOD=$(kubectl get pods -l app=mysql-instance -o jsonpath="{.items[*].metadata.name}")
$
$ kubectl exec -it $MYSQLPOD -- mysql -u root -potuspassword -e "CREATE TABLE test (id smallint unsigned not null auto_increment, name varchar(20) not null, constraint pk_example primary key (id) );" otus-database
mysql: [Warning] Using a password on the command line interface can be insecure.
$
$ kubectl exec -it $MYSQLPOD -- mysql -potuspassword -e "INSERT INTO test ( id, name) VALUES ( null, 'some data' );" otus-database
mysql: [Warning] Using a password on the command line interface can be insecure.
$
$ kubectl exec -it $MYSQLPOD -- mysql -potuspassword -e "INSERT INTO test ( id, name) VALUES ( null, 'some data-2' );" otus-database
mysql: [Warning] Using a password on the command line interface can be insecure.
```
11. Посмотри содержимое таблицы:
```bash
$ kubectl exec -it $MYSQLPOD -- mysql -potuspassword -e "select * from test;" otus-database
mysql: [Warning] Using a password on the command line interface can be insecure.
+----+-------------+
| id | name        |
+----+-------------+
|  1 | some data   |
|  2 | some data-2 |
+----+-------------+
```
12. Удалим mysql-instance и создадим его заново:
```bash
$ kubectl delete ms mysql-instance
mysql.otus.homework "mysql-instance" deleted
$
$ kubectl apply -f kubernetes-operators/deploy/cr.yaml
mysql.otus.homework/mysql-instance created
```
13. Проверим, что наши данные восстановились из бэкапа:
```bash
$ export MYSQLPOD=$(kubectl get pods -l app=mysql-instance -o jsonpath="{.items[*].metadata.name}")
$
$ kubectl exec -it $MYSQLPOD -- mysql -potuspassword -e "select * from test;" otus-database
mysql: [Warning] Using a password on the command line interface can be insecure.
+----+-------------+
| id | name        |
+----+-------------+
|  1 | some data   |
|  2 | some data-2 |
+----+-------------+
```

### Задание 3. MySQL оператор | Сборка и деплой контроллера
---

1. На основе [Dockerfile](../kubernetes-operators/build/Dockerfile) был собран образ `vasiilij/mysql-operator:0.1.0` с mysql контроллером и загружен в DockerHub.
2. Для деплоя контроллера были созданы следующие манифесты:
   1. [service-account.yaml](../kubernetes-operators/deploy/service-account.yaml)
   2. [role.yaml](../kubernetes-operators/deploy/role.yaml)
   3. [role-binding.yaml](../kubernetes-operators/deploy/role-binding.yaml)
   4. [deployment.yaml](../kubernetes-operators/deploy/deployment.yaml)
3. После применения манифестов проверим, что всё работает:
   1. Удалим ранее созданный объект `mysql-instance`:
```bash
$ kubectl delete ms mysql-instance
mysql.otus.homework "mysql-instance" deleted
```
   2. Создадим новый и проверим, что данные на месте, плюс добавим новую строку в таблицу:
```bash
$ kubectl apply -f kubernetes-operators/deploy/cr.yaml
mysql.otus.homework/mysql-instance created
$
$ kubectl get pvc
NAME                        STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
backup-mysql-instance-pvc   Bound    pvc-4530b593-617a-460a-a9be-2d6a754a5455   1Gi        RWO            standard       137m
mysql-instance-pvc          Bound    pvc-66087d75-491e-4161-b131-3e7844e4af79   1Gi        RWO            standard       5m14s
$
$ kubectl get jobs.batch
NAME                         COMPLETIONS   DURATION   AGE
backup-mysql-instance-job    1/1           4s         19m
restore-mysql-instance-job   1/1           43s        17m
$
$ export MYSQLPOD=$(kubectl get pods -l app=mysql-instance -o jsonpath="{.items[*].metadata.name}")
$ kubectl exec -it $MYSQLPOD -- mysql -potuspassword -e "INSERT INTO test ( id, name ) VALUES ( null, 'some data-3' );" otus-database
$ kubectl exec -it $MYSQLPOD -- mysql -potuspassword -e "select * from test;" otus-database
mysql: [Warning] Using a password on the command line interface can be insecure.
+----+-------------+
| id | name        |
+----+-------------+
|  1 | some data   |
|  2 | some data-2 |
|  3 | some data-3 |
+----+-------------+
```
   3. Логи контроллера:
```bash
$ kubectl logs mysql-operator-58cddcb474-tb8mw 
/usr/local/lib/python3.10/site-packages/kopf/_core/reactor/running.py:179: FutureWarning: Absence of either namespaces or cluster-wide flag will become an error soon. For now, switching to the cluster-wide mode for backward compatibility.
  warnings.warn("Absence of either namespaces or cluster-wide flag will become an error soon."
[2024-02-05 19:27:33,216] kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
[2024-02-05 19:27:33,218] kopf.activities.auth [INFO    ] Activity 'login_via_client' succeeded.
[2024-02-05 19:27:33,218] kopf._core.engines.a [INFO    ] Initial authentication has finished.
[2024-02-19 20:15:07,492] kopf.objects         [INFO    ] [default/mysql-instance] MySQL instance mysql-instance and its children resources deleted!
[2024-02-19 20:15:07,498] kopf.objects         [INFO    ] [default/mysql-instance] Handler 'delete_object_make_backup' succeeded.
[2024-02-19 20:15:07,500] kopf.objects         [INFO    ] [default/mysql-instance] Deletion is processed: 1 succeeded; 0 failed.
[2024-02-19 20:15:07,526] kopf.objects         [WARNING ] [default/mysql-instance] Patching failed with inconsistencies: (('remove', ('status',), {'delete_object_make_backup': {'message': 'MySQL instance mysql-instance and its children resources deleted!'}}, None),)
[2024-02-19 20:16:06,937] kopf.objects         [INFO    ] [default/mysql-instance] Creating pv, pvc for mysql data and svc...
[2024-02-19 20:16:07,000] kopf.objects         [INFO    ] [default/mysql-instance] Creating mysql deployment...
[2024-02-19 20:16:07,020] kopf.objects         [INFO    ] [default/mysql-instance] Waiting for mysql deployment to become ready...
[2024-02-19 20:16:17,049] kopf.objects         [INFO    ] [default/mysql-instance] Trying to restore from backup...
[2024-02-19 20:16:17,090] kopf.objects         [INFO    ] [default/mysql-instance] {'active': None,
 'completed_indexes': None,
 'completion_time': None,
 'conditions': None,
 'failed': None,
 'failed_indexes': None,
 'ready': None,
 'start_time': None,
 'succeeded': None,
 'terminating': None,
 'uncounted_terminated_pods': None}
[2024-02-19 20:16:17,093] kopf.objects         [INFO    ] [default/mysql-instance] MySQL instance mysql-instance and its children resources created!
[2024-02-19 20:16:17,095] kopf.objects         [INFO    ] [default/mysql-instance] Handler 'mysql_on_create' succeeded.
[2024-02-19 20:16:17,095] kopf.objects         [INFO    ] [default/mysql-instance] Creation is processed: 1 succeeded; 0 failed.
[2024-02-19 20:16:17,111] kopf.objects         [WARNING ] [default/mysql-instance] Patching failed with inconsistencies: (('remove', ('status',), {'mysql_on_create': {'message': 'MySQL instance mysql-instance and its children resources created!'}}, None),)
```
   4. Вывод команды `kubectl get jobs` с успешно выполненными backup и restore job:
```bash
$ kubectl get jobs
NAME                         COMPLETIONS   DURATION   AGE
backup-mysql-instance-job    1/1           3s         2m37s
restore-mysql-instance-job   1/1           9s         83s
```
