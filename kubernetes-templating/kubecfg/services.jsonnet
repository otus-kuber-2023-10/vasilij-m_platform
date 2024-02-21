local kube = import 'https://raw.githubusercontent.com/kube-libsonnet/kube-libsonnet/v1.22.2/kube.libsonnet';

local registry = "gcr.io/google-samples/microservices-demo";
local app_version = "v0.8.0";
local grpc_port_name = "grpc";
local grpc_port_number = 50051;

local common(name) = {
  deployment: kube.Deployment(name) {
    spec+: {
      template+: {
        spec+: {
          serviceAccountName: "default",
          securityContext: {
            fsGroup: 1000,
            runAsGroup: 1000,
            runAsNonRoot: true,
            runAsUser: 1000,
          },
          containers_+: {
            common: kube.Container("common") {
              name: "common",
              image: registry + "/" + name + ":" + app_version,
              securityContext: {
                allowPrivilegeEscalation: false,
                capabilities: {
                  drop: ["ALL"],
                },
                privileged: false,
                readOnlyRootFilesystem: true,
              },
              env: [
                {
                  name: "PORT", 
                  value: std.toString(grpc_port_number),
                },
                {
                  name: "DISABLE_PROFILER", 
                  value: "1",
                },                
              ],
              ports: [
                { 
                  name: grpc_port_name,
                  containerPort: grpc_port_number,
                }
              ],
              readinessProbe: {
                grpc: {
                  port: grpc_port_number,
                },
              },
              livenessProbe: {
                grpc: {
                  port: grpc_port_number,
                },
              },
              resources: {
                requests: {
                  cpu: '100m',
                  memory: '64Mi',
                },
                limits: {
                  cpu: '200m',
                  memory: '128Mi',
                },
              },
            },
          },
        },
      },
    },
  },

  service: kube.Service(name) {
    target_pod:: $.deployment.spec.template,
  },
};

{
  paymentservice: common("paymentservice") {
    deployment+: {
      spec+: {
        minReadySeconds: 0,
        template+: {
          spec+: {
            terminationGracePeriodSeconds: 5,
            containers_+: {
              common+: {
                name: "server",
              },
            },
          },
        },
      },
    },
  },

  shippingservice: common("shippingservice") {
    deployment+: {
      spec+: {
        minReadySeconds: 0,
        template+: {
          spec+: {
            containers_+: {
              common+: {
                name: "server",
                readinessProbe+: {
                  periodSeconds: 5,
                },
              },
            },
          },
        },
      },
    },
  },
}

// {
//   paymentservice_deployment: common("paymentservice"),
//   shippingservice_deployment: common("shippingservice"),
// }
