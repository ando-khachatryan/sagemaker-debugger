import numpy as np
import typing as Tuple
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data


### Used for tf.estimator.Estimator ###


def get_estimator() -> tf.estimator.Estimator:
    """ Return an estimator object ready for testing. """
    return tf.estimator.Estimator(model_fn=_cnn_model_fn, model_dir="/tmp/mnist_model")


def get_input_fns(n_examples=32) -> Tuple:
    # Load training and eval data
    ((train_data, train_labels), (eval_data, eval_labels)) = tf.keras.datasets.mnist.load_data()

    train_data = train_data / np.float32(255)
    train_labels = train_labels.astype(np.int32)  # not required

    eval_data = eval_data / np.float32(255)
    eval_labels = eval_labels.astype(np.int32)  # not required

    train_data, train_labels, eval_data, eval_labels = (
        train_data[:n_examples],
        train_labels[:n_examples],
        eval_data[:n_examples],
        eval_labels[:n_examples],
    )

    train_input_fn = tf.estimator.inputs.numpy_input_fn(
        x={"x": train_data}, y=train_labels, batch_size=n_examples, num_epochs=5, shuffle=True
    )

    eval_input_fn = tf.estimator.inputs.numpy_input_fn(
        x={"x": eval_data}, y=eval_labels, num_epochs=1, shuffle=False
    )

    return train_input_fn, eval_input_fn


def _cnn_model_fn(features, labels, mode):
    """Model function for CNN."""
    # Input Layer
    input_layer = tf.reshape(features["x"], [-1, 28, 28, 1])

    # Convolutional Layer #1
    conv1 = tf.layers.conv2d(
        inputs=input_layer, filters=32, kernel_size=[5, 5], padding="same", activation=tf.nn.relu
    )

    # Pooling Layer #1
    pool1 = tf.layers.max_pooling2d(inputs=conv1, pool_size=[2, 2], strides=2)

    # Convolutional Layer #2 and Pooling Layer #2
    conv2 = tf.layers.conv2d(
        inputs=pool1, filters=64, kernel_size=[5, 5], padding="same", activation=tf.nn.relu
    )
    pool2 = tf.layers.max_pooling2d(inputs=conv2, pool_size=[2, 2], strides=2)

    # Dense Layer
    pool2_flat = tf.reshape(pool2, [-1, 7 * 7 * 64])
    dense = tf.layers.dense(inputs=pool2_flat, units=1024, activation=tf.nn.relu)
    dropout = tf.layers.dropout(
        inputs=dense, rate=0.4, training=mode == tf.estimator.ModeKeys.TRAIN
    )

    # Logits Layer
    logits = tf.layers.dense(inputs=dropout, units=10)

    predictions = {
        # Generate predictions (for PREDICT and EVAL mode)
        "classes": tf.argmax(input=logits, axis=1),
        # Add `softmax_tensor` to the graph. It is used for PREDICT and by the
        # `logging_hook`.
        "probabilities": tf.nn.softmax(logits, name="softmax_tensor"),
    }

    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions)

    # Calculate Loss (for both TRAIN and EVAL modes)
    loss = tf.reduce_mean(
        tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels, logits=logits)
    )
    loss = tf.losses.sparse_softmax_cross_entropy(labels=labels, logits=logits)
    tf.summary.scalar("loss", loss)

    # Configure the Training Op (for TRAIN mode)
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.GradientDescentOptimizer(learning_rate=0.001)
        # optimizer = ts.TornasoleOptimizer(optimizer)
        train_op = optimizer.minimize(loss=loss, global_step=tf.train.get_global_step())
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op)

    # Add evaluation metrics (for EVAL mode)
    eval_metric_ops = {
        "accuracy": tf.metrics.accuracy(labels=labels, predictions=predictions["classes"])
    }
    return tf.estimator.EstimatorSpec(mode=mode, loss=loss, eval_metric_ops=eval_metric_ops)


### Used for tf.Session ###


def get_train_op_and_placeholders():
    # Parameters
    learning_rate = 0.1
    num_steps = 200  # 500
    batch_size = 128
    display_step = 100

    # Network Parameters
    n_hidden_1 = 256  # 1st layer number of neurons
    n_hidden_2 = 256  # 2nd layer number of neurons
    num_input = 784  # MNIST data input (img shape: 28*28)
    num_classes = 10  # MNIST total classes (0-9 digits)

    # tf Graph input
    X = tf.compat.v1.placeholder("float", [None, num_input])
    Y = tf.compat.v1.placeholder("float", [None, num_classes])

    # Store layers weight & bias
    weights = {
        "h1": tf.Variable(tf.random.normal([num_input, n_hidden_1]), name="h1"),
        "h2": tf.Variable(tf.random.normal([n_hidden_1, n_hidden_2]), name="h2"),
        "out": tf.Variable(tf.random.normal([n_hidden_2, num_classes]), name="h_out"),
    }
    biases = {
        "b1": tf.Variable(tf.random.normal([n_hidden_1]), name="b1"),
        "b2": tf.Variable(tf.random.normal([n_hidden_2]), name="b2"),
        "out": tf.Variable(tf.random.normal([num_classes]), name="b_out"),
    }

    # Create model
    def neural_net(x):
        # Hidden fully connected layer with 256 neurons
        layer_1 = tf.add(tf.matmul(x, weights["h1"]), biases["b1"])
        # Hidden fully connected layer with 256 neurons
        layer_2 = tf.add(tf.matmul(layer_1, weights["h2"]), biases["b2"])
        # Output fully connected layer with a neuron for each class
        out_layer = tf.matmul(layer_2, weights["out"]) + biases["out"]
        return out_layer

    # Construct model
    logits = neural_net(X)
    prediction = tf.nn.softmax(logits)

    # Define loss and optimizer
    loss_op = tf.compat.v1.losses.softmax_cross_entropy(onehot_labels=Y, logits=logits)
    # Using a functional loss will fail because TF optimizes away the mean.
    # See https://stackoverflow.com/questions/58532324/tf-gradients-dont-flow-through-tf-reduce-mean
    # loss_op = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=logits, labels=Y))
    optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=learning_rate)
    train_op = optimizer.minimize(loss_op)
    # Evaluate model
    correct_pred = tf.equal(tf.argmax(prediction, 1), tf.argmax(Y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    # Initialize the variables (i.e. assign their default value)
    init = tf.compat.v1.global_variables_initializer()
    return train_op, X, Y


def get_data() -> "tf.contrib.learn.python.learn.datasets.base.Datasets":
    mnist = input_data.read_data_sets("/tmp/data/", one_hot=True)
    return mnist


### Used for tf.keras


def get_keras_data(n_examples=32) -> Tuple:
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    x_train = x_train.reshape(60000, 784).astype("float32") / 255
    x_test = x_test.reshape(10000, 784).astype("float32") / 255
    return (x_train[:n_examples], y_train[:n_examples]), (x_test[:n_examples], y_test[:n_examples])


def get_keras_model_v1():
    import tensorflow.compat.v1.keras as keras

    inputs = keras.Input(shape=(784,), name="img")
    x = keras.layers.Dense(64, activation="relu")(inputs)
    x = keras.layers.Dense(64, activation="relu")(x)
    outputs = keras.layers.Dense(10, activation="softmax")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="mnist_model")
    return model