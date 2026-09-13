// AGENT-085 trigger: math/rand used where crypto/rand is required.
package agent

import (
	"fmt"
	"math/rand"
)

// SessionToken mints a session identifier for the agent.
func SessionToken() string {
	return fmt.Sprintf("sess-%d", rand.Int63())
}
