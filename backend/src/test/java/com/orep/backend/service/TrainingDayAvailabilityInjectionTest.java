package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TrainingDayAvailabilityInjectionTest {

    @Test
    void productionServicesDeclareAvailabilityServiceConstructorDependency() {
        assertHasAvailabilityDependency(ProjectTeamService.class);
        assertHasAvailabilityDependency(TeacherPortalService.class);
        assertHasAvailabilityDependency(TrainingDayLearningResourceService.class);
    }

    @Test
    void studentTrainingServiceHasNoConstructorThatCreatesAvailabilityInternally() {
        boolean hasLegacyConstructor = Arrays.stream(StudentTrainingService.class.getConstructors())
                .anyMatch(constructor -> constructor.getParameterCount() == 3);
        assertFalse(hasLegacyConstructor);
    }

    private void assertHasAvailabilityDependency(Class<?> serviceType) {
        boolean declared = Arrays.stream(serviceType.getConstructors())
                .anyMatch(constructor -> Arrays.asList(constructor.getParameterTypes())
                        .contains(TrainingDayAvailabilityService.class));
        assertTrue(declared, () -> serviceType.getSimpleName()
                + " must inject TrainingDayAvailabilityService through its production constructor");
    }
}
