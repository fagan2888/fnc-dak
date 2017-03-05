import logging

import tensorflow as tf
from util import ConfusionMatrix, Progbar, minibatches, LBLS, RELATED

logger = logging.getLogger("baseline")
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

class Model(object):
    """Abstracts a Tensorflow graph for a learning task.

    We use various Model classes as usual abstractions to encapsulate tensorflow
    computational graphs. Each algorithm you will construct in this homework will
    inherit from a Model object.
    """
    def add_placeholders(self):
        """Adds placeholder variables to tensorflow computational graph.

        Tensorflow uses placeholder variables to represent locations in a
        computational graph where data is inserted.  These placeholders are used as
        inputs by the rest of the model building and will be fed data during
        training.

        See for more information:
        https://www.tensorflow.org/versions/r0.7/api_docs/python/io_ops.html#placeholders
        """
        raise NotImplementedError("Each Model must re-implement this method.")

    def create_feed_dict(self, inputs_batch, labels_batch=None):
        """Creates the feed_dict for one step of training.

        A feed_dict takes the form of:
        feed_dict = {
                <placeholder>: <tensor of values to be passed for placeholder>,
                ....
        }

        If labels_batch is None, then no labels are added to feed_dict.

        Hint: The keys for the feed_dict should be a subset of the placeholder
                    tensors created in add_placeholders.
        Args:
            inputs_batch: A batch of input data.
            labels_batch: A batch of label data.
        Returns:
            feed_dict: The feed dictionary mapping from placeholders to values.
        """
        raise NotImplementedError("Each Model must re-implement this method.")

    def add_prediction_op(self):
        """Implements the core of the model that transforms a batch of input data into predictions.

        Returns:
            pred: A tensor of shape (batch_size, n_classes)
        """
        raise NotImplementedError("Each Model must re-implement this method.")

    def add_loss_op(self, pred):
        """Adds Ops for the loss function to the computational graph.

        Args:
            pred: A tensor of shape (batch_size, n_classes)
        Returns:
            loss: A 0-d tensor (scalar) output
        """
        raise NotImplementedError("Each Model must re-implement this method.")

    def add_training_op(self, loss):
        """Sets up the training Ops.

        Creates an optimizer and applies the gradients to all trainable variables.
        The Op returned by this function is what must be passed to the
        sess.run() to train the model. See

        https://www.tensorflow.org/versions/r0.7/api_docs/python/train.html#Optimizer

        for more information.

        Args:
            loss: Loss tensor (a scalar).
        Returns:
            train_op: The Op for training.
        """

        raise NotImplementedError("Each Model must re-implement this method.")

    def train_on_batch(self, sess, headlines_batch, bodies_batch, labels_batch):
        """Perform one step of gradient descent on the provided batch of data.

        Args:
            sess: tf.Session()
            input_batch: np.ndarray of shape (n_samples, n_features)
            labels_batch: np.ndarray of shape (n_samples, n_classes)
        Returns:
            loss: loss over the batch (a scalar)
        """
        feed = self.create_feed_dict(headlines_batch, bodies_batch,
            labels_batch=labels_batch)
        _, loss = sess.run([self.train_op, self.loss], feed_dict=feed)
        return loss


    def predict_on_batch(self, sess, headlines_batch, bodies_batch):
        """Make predictions for the provided batch of data

        Args:
            sess: tf.Session()
            input_batch: np.ndarray of shape (n_samples, n_features)
        Returns:
            predictions: np.ndarray of shape (n_samples, n_classes)
        """
        feed = self.create_feed_dict(headlines_batch, bodies_batch)
        predictions = sess.run(tf.argmax(self.pred, axis=1), feed_dict=feed)
        return predictions


    def output(self, sess, inputs):
        """
        Reports the output of the model on examples.
        """

        preds = []
        headlines, bodies, stances = zip(*inputs)
        data = zip(headlines, bodies)
        prog = Progbar(target=1 + int(len(stances) / self.config.batch_size))
        # TODO(akshayka): Verify that data is in the correct structure
        for i, batch in enumerate(minibatches(data, self.config.batch_size,
            shuffle=False)):
            preds_ = self.predict_on_batch(sess, *batch)
            preds += list(preds_)
            prog.update(i + 1, [])
        return (headlines, bodies), stances, preds


    def evaluate(self, sess, examples):
        """Evaluates model performance on @examples.

        This function uses the model to predict labels for @examples and
        constructs a confusion matrix.

        Args:
            sess: the current TensorFlow session.
            examples: A list of vectorized input/output pairs.
        Returns:
            The F1 score for predicting the relationship between
            headline-body pairs
        """
        # TODO(akshayka): Implement a report that tells us the inputs
        # on which we guessed incorrectly
        token_cm = ConfusionMatrix(labels=LBLS)

        correct_guessed_related, total_gold_related, total_guessed_related = (
            0., 0., 0.)
        _, labels, labels_ = self.output(sess, examples)
        for l, l_ in zip(labels, labels_):
            token_cm.update(l, l_)
            if l == l_ and l in RELATED:
                correct_guessed_related += 1
            if l in RELATED:
                total_gold_related += 1
            if l_ in RELATED:
                total_guessed_related += 1

        p = correct_guessed_related / total_guessed_related if \
            total_guessed_related > 0 else 0
        r = correct_guessed_related / total_gold_related if \
            total_gold_related > 0 else 0

        if total_guessed_related == 0:
            logging.warn("total_guessed_related == 0!")
        if total_gold_related == 0:
            logging.warn("total_gold_related == 0!")
        f1 = 2 * p * r / (p + r) if p + r > 0 else 0
        return token_cm, (p, r, f1)


    def run_epoch(self, sess, train_examples, dev_examples):
        prog = Progbar(target=1 + int(len(train_examples) /
            self.config.batch_size))
        for i, batch in enumerate(minibatches(train_examples,
            self.config.batch_size)):
            loss = self.train_on_batch(sess, *batch)
            prog.update(i + 1, [("train loss", loss)])
        print("")

        #logger.info("Evaluating on training data")
        #token_cm, entity_scores = self.evaluate(sess, train_examples, train_examples_raw)
        #logger.debug("Token-level confusion matrix:\n" + token_cm.as_table())
        #logger.debug("Token-level scores:\n" + token_cm.summary())
        #logger.info("Entity level P/R/F1: %.2f/%.2f/%.2f", *entity_scores)

        logger.info("Evaluating on development data")
        token_cm, entity_scores = self.evaluate(sess, dev_examples)
        logger.debug("Token-level confusion matrix:\n" + token_cm.as_table())
        logger.debug("Token-level scores:\n" + token_cm.summary())
        logger.info("Entity level P/R/F1: %.2f/%.2f/%.2f", *entity_scores)

        f1 = entity_scores[-1]
        return f1
        


    def fit(self, sess, saver, train_examples, dev_examples):
        best_score = 0.

        for epoch in range(self.config.n_epochs):
            logger.info("Epoch %d out of %d", epoch + 1, self.config.n_epochs)
            score = self.run_epoch(sess, train_examples, dev_examples)
            if score > best_score:
                best_score = score
                if saver:
                    logger.info("New best score! Saving model in %s", self.config.model_output)
                    saver.save(sess, self.config.model_output)
            print("")
        return best_score
    

    def build(self):
        self.add_placeholders()
        self.pred = self.add_prediction_op()
        self.loss = self.add_loss_op(self.pred)
        self.train_op = self.add_training_op(self.loss)
