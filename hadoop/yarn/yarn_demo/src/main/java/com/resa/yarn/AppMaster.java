/*
* Simple YARN Application Skeleton
* Copyright (C) 2015 George Piskas, Philémon Favrod
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License along
* with this program; if not, write to the Free Software Foundation, Inc.,
* 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*
* Contact: geopiskas@gmail.com
*/


package com.resa.yarn;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.hadoop.yarn.api.ApplicationConstants;
import org.apache.hadoop.yarn.api.records.Container;
import org.apache.hadoop.yarn.api.records.ContainerLaunchContext;
import org.apache.hadoop.yarn.api.records.ContainerStatus;
import org.apache.hadoop.yarn.api.records.FinalApplicationStatus;
import org.apache.hadoop.yarn.api.records.LocalResource;
import org.apache.hadoop.yarn.api.records.NodeReport;
import org.apache.hadoop.yarn.api.records.Priority;
import org.apache.hadoop.yarn.api.records.Resource;
import org.apache.hadoop.yarn.client.api.AMRMClient.ContainerRequest;
import org.apache.hadoop.yarn.client.api.NMClient;
import org.apache.hadoop.yarn.client.api.async.AMRMClientAsync;
import org.apache.hadoop.yarn.conf.YarnConfiguration;
import org.apache.hadoop.yarn.util.Records;

public class AppMaster implements AMRMClientAsync.CallbackHandler {

    private YarnConfiguration conf = new YarnConfiguration();
    private NMClient nmClient;
    private int containerCount = 4;

    public static void main(String[] args) {
        System.out.println("AppMaster: Initializing");
        try {
            new AppMaster().run();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

    public void run() throws Exception {
        conf = new YarnConfiguration();

        // Create NM Client
        nmClient = NMClient.createNMClient();
        nmClient.init(conf);
        nmClient.start();

        // Create AM - RM Client
        AMRMClientAsync<ContainerRequest> rmClient = AMRMClientAsync.createAMRMClientAsync(1000, this);
        rmClient.init(conf);
        rmClient.start();

        // Register with RM
        rmClient.registerApplicationMaster("", 0, "");
        System.out.println("AppMaster: Registered");

        // Priority for worker containers - priorities are intra-application
        Priority priority = Records.newRecord(Priority.class);
        priority.setPriority(0);

        // Resource requirements for worker containers
        Resource capability = Records.newRecord(Resource.class);
        capability.setMemory(128);
        capability.setVirtualCores(1);

        // Reqiest Containers from RM
        System.out.println("AppMaster: Requesting " + containerCount + " Containers");
        for (int i = 0; i < containerCount; ++i) {
            rmClient.addContainerRequest(new ContainerRequest(capability, null, null, priority));
        }

        while (!containersFinished()) {
            Thread.sleep(100);
        }

        System.out.println("AppMaster: Unregistered");
        rmClient.unregisterApplicationMaster(FinalApplicationStatus.SUCCEEDED, "", "");
    }

    private boolean containersFinished() {
        return containerCount == 0;
    }

    @Override
    public void onContainersAllocated(List<Container> containers) {
        for (Container container : containers) {
            try {
                nmClient.startContainer(container, initContainer());
                System.err.println("AppMaster: Container launched " + container.getId());
            } catch (Exception ex) {
                System.err.println("AppMaster: Container not launched " + container.getId());
                ex.printStackTrace();
            }
        }
    }

    private ContainerLaunchContext initContainer() {
        try {
            // Create Container Context
            ContainerLaunchContext cCLC = Records.newRecord(ContainerLaunchContext.class);
            cCLC.setCommands(Collections.singletonList("$JAVA_HOME/bin/java"
                    + " -Xmx256M"
                    + " com.resa.yarn.Container"
                    + " 1>" + ApplicationConstants.LOG_DIR_EXPANSION_VAR + "/stdout"
                    + " 2>" + ApplicationConstants.LOG_DIR_EXPANSION_VAR + "/stderr"));

            // Set Container jar
            LocalResource jar = Records.newRecord(LocalResource.class);
            Utils.setUpLocalResource(Utils.YARNAPP_JAR_PATH, jar, conf);
            cCLC.setLocalResources(Collections.singletonMap(Utils.YARNAPP_JAR_NAME, jar));

            // Set Container CLASSPATH
            Map<String, String> env = new HashMap<String, String>();
            Utils.setUpEnv(env, conf);
            cCLC.setEnvironment(env);

            return cCLC;
        } catch (Exception ex) {
            ex.printStackTrace();
            return null;
        }
    }

    @Override
    public void onContainersCompleted(List<ContainerStatus> statusOfContainers) {
        for (ContainerStatus status : statusOfContainers) {
            System.err.println("AppMaster: Container finished " + status.getContainerId());
            synchronized (this) {
                containerCount--;
            }
        }
    }

    @Override
    public void onError(Throwable e) {}

    @Override
    public void onNodesUpdated(List<NodeReport> nodeReports) {}

    @Override
    public void onShutdownRequest() {}

    @Override
    public float getProgress() {
        return 0;
    }
}