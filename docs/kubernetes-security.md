### Задание 1
---
1. Создать Service Account `bob` , дать ему роль `admin` в рамках всего кластера
2. Создать Service Account `dave` без доступа к кластеру

**Выполнение**  

1. Service Account `bob` и ClusterRoleBinding `admin-clusterrole` описаны в манифестах `./kubernetes-security/task01/01-sa-bob.yaml` и `./kubernetes-security/task01/02-clusterrolebinding-bob.yaml`.
2. Service Account `dave` описан в манифесте `./kubernetes-security/task01/03-sa-dave.yaml`. Чтобы у `dave` не было доступа к кластеру достаточно просто не привязывать его к какой-либо роли через объекты RoleBinding/ClusterRoleBinding.

### Задание 2
---
1. Создать Namespace `prometheus`
2. Создать Service Account `carol` в этом Namespace
3. Дать всем Service Account в Namespace `prometheus` возможность делать `get`, `list`, `watch` в отношении Pods всего кластера

**Выполнение**

1. Namespace `prometheus` описано в манифесте `./kubernetes-security/task02/01-namespace.yaml`.
2. Service Account `carol` описан в манифесте `./kubernetes-security/task02/02-sa-carol.yaml`.
3. Чтобы все сервисные аккаунты в Namespace `prometheus` имели возможность делать `get`, `list`, `watch` в отношении Pods всего кластера, нужно применить следующие манифесты:
  1.  `./kubernetes-security/task02/03-clusterrole-pods-viewer.yaml` - описывает ClusterRole `pods-viewer`
  2.  `./kubernetes-security/task02/04-clusterrolebinding-pods-viewer.yaml` - описывает ClusterRoleBinding `serviceaccounts-pods-viewer` (привязывает сервисные аккаунты из Namespace `prometheus` к ClusterRole `pods-viewer`).

### Задание 3
---
1. Создать Namespace `dev`
2. Создать Service Account `jane` в Namespace `dev`
3. Дать `jane` роль `admin` в рамках Namespace `dev`
4. Создать Service Account `ken` в Namespace `dev`
4. Дать `ken` роль `view` в рамках Namespace `dev`

**Выполнение**
  
1. Namespace `dev` описано в манифесте `./kubernetes-security/task03/01-namespace.yaml`.
2. Service Account `jane` описан в манифесте `./kubernetes-security/task03/02-sa-jane.yaml`.
3. Манифест `./kubernetes-security/task03/03-rolebinding-jane.yaml` - описывает RoleBinding `jane-admin` в рамках Namespace `dev` (привязывает сервисный аккаунт `jane` из Namespace `dev` к ClusterRole `admin`).
4. Service Account `ken` описан в манифесте `./kubernetes-security/task03/04-sa-ken.yaml`.
5. Манифест `./kubernetes-security/task03/05-rolebinding-ken.yaml` - описывает RoleBinding `ken-view` в рамках Namespace `dev` (привязывает сервисный аккаунт `ken` из Namespace `dev` к ClusterRole `view`).
