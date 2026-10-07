allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}

subprojects {
    val configureCompileSdk = {
        val android = project.extensions.findByName("android")
        if (android != null) {
            for (method in android.javaClass.methods) {
                if (method.name == "compileSdkVersion" || method.name == "setCompileSdk" || method.name == "setCompileSdkVersion") {
                    try {
                        if (method.parameterCount == 1 && (method.parameterTypes[0] == Int::class.javaPrimitiveType || method.parameterTypes[0] == java.lang.Integer::class.java)) {
                            method.invoke(android, 36)
                        }
                    } catch (_: Exception) {}
                }
            }
        }
    }

    if (state.executed) {
        configureCompileSdk()
    } else {
        afterEvaluate {
            configureCompileSdk()
        }
    }

    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
